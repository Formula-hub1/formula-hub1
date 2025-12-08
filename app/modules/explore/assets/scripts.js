document.addEventListener('DOMContentLoaded', () => {
    // 1. Asignar listeners a los filtros (solo una vez)
    setupFilterListeners();

    // 2. Comprobar parámetros de URL y ejecutar la búsqueda inicial
    handleInitialLoad();
});

// Función central: Se encarga ÚNICAMENTE de ejecutar el FETCH y renderizar los resultados.
function performSearch() {
    const headerQueryInput = document.getElementById('search-query');
    const sidebarQueryInput = document.getElementById('query');

    // 1. Verificamos que ambos inputs existan.
    // 2. Comparamos sus VALORES (.value), no los elementos.
    // 3. Copiamos del Sidebar AL Header (porque aquí es donde estás escribiendo).
    if (headerQueryInput && sidebarQueryInput) {
        if (headerQueryInput.value !== sidebarQueryInput.value) {
            headerQueryInput.value = sidebarQueryInput.value;
        }
    }

    console.log("performing search...");

    // Limpiar resultados y ocultar el icono de "No encontrado"
    document.getElementById('results').innerHTML = '';
    document.getElementById("results_not_found").style.display = "none";
    console.log("hide not found icon");

    const csrfToken = document.getElementById('csrf_token').value;

    const searchCriteria = {
        csrf_token: csrfToken,
        query: document.querySelector('#query').value, // Obtener el valor de la barra de búsqueda
        publication_type: document.querySelector('#publication_type').value, // Obtener el valor del filtro de tipo de publicación
        sorting: document.querySelector('[name="sorting"]:checked').value, // Obtener el valor del filtro de ordenamiento
    };

    // Obtengo aquí los valores de la busqueda del advanced filter
    // Uso ? para el manejejo de elementos solo existentes en base_template.html
    searchCriteria.author = document.getElementById('filter-author')?.value || '';
    searchCriteria.description = document.getElementById('filter-description')?.value || '';
    searchCriteria.uvl_files = document.getElementById('filter-file')?.value || '';
    searchCriteria.date = document.getElementById('filter-date')?.value || '';
    const tagsInput = document.getElementById('filter-tags-nav');
    if (tagsInput && tagsInput.value.trim() !== '') {
        // Separamos por comas, quitamos espacios en blanco y creamos el array
        // Ejemplo: "f1, racing" -> ["f1", "racing"]
        searchCriteria.tags = tagsInput.value.split(',').map(tag => tag.trim());
    } else {
        searchCriteria.tags = [];
    }
    console.log("Criteria to send:", searchCriteria);


    console.log(`Filtros: Query='${searchCriteria.query}', Type='${searchCriteria.publication_type}', Sorting='${searchCriteria.sorting}'`);

    fetch('/explore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchCriteria),
    })
    .then(response => response.json())
    .then(data => {

        console.log("Data received:", data);
        document.getElementById('results').innerHTML = '';

        // results counter
        const resultCount = data.length;
        const resultText = resultCount === 1 ? 'dataset' : 'datasets';
        document.getElementById('results_number').textContent = `${resultCount} ${resultText} found`;

        if (resultCount === 0) {
            console.log("show not found icon");
            document.getElementById("results_not_found").style.display = "block";
        } else {
            document.getElementById("results_not_found").style.display = "none";
        }


        data.forEach(dataset => {
            let card = document.createElement('div');
            card.className = 'col-12';
            card.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center justify-content-between">
                            <h3><a href="${dataset.url}">${dataset.title}</a></h3>
                            <div>
                                <span class="badge bg-primary" style="cursor: pointer;" onclick="set_publication_type_as_query('${dataset.publication_type}')">${dataset.publication_type}</span>
                            </div>
                        </div>
                        <p class="text-secondary">${formatDate(dataset.created_at)}</p>

                        <div class="row mb-2">

                            <div class="col-md-4 col-12">
                                <span class=" text-secondary">
                                    Description
                                </span>
                            </div>
                            <div class="col-md-8 col-12">
                                <p class="card-text">${dataset.description}</p>
                            </div>

                        </div>

                        <div class="row mb-2">

                            <div class="col-md-4 col-12">
                                <span class=" text-secondary">
                                    Authors
                                </span>
                            </div>
                            <div class="col-md-8 col-12">
                                ${dataset.authors.map(author => `
                                    <p class="p-0 m-0">${author.name}${author.affiliation ? ` (${author.affiliation})` : ''}${author.orcid ? ` (${author.orcid})` : ''}</p>
                                `).join('')}
                            </div>

                        </div>

                        <div class="row mb-2">

                            <div class="col-md-4 col-12">
                                <span class=" text-secondary">
                                    Tags
                                </span>
                            </div>
                            <div class="col-md-8 col-12">
                                ${dataset.tags.map(tag => `<span class="badge bg-primary me-1" style="cursor: pointer;" onclick="set_tag_as_query('${tag}')">${tag}</span>`).join('')}
                            </div>

                        </div>

                        <div class="row">

                            <div class="col-md-4 col-12">

                            </div>
                            <div class="col-md-8 col-12">
                                <a href="${dataset.url}" class="btn btn-outline-primary btn-sm" id="search" style="border-radius: 5px;">
                                    View dataset
                                </a>
                                <a href="/dataset/download/${dataset.id}" class="btn btn-outline-primary btn-sm" id="search" style="border-radius: 5px;">
                                    Download (${dataset.total_size_in_human_format})
                                </a>
                            </div>


                        </div>

                    </div>
                </div>
            `;

            document.getElementById('results').appendChild(card);
        });
    })
    .catch(error => console.error('Error during search:', error));
}

// Función para asignar listeners a los filtros
function setupFilterListeners() {
    const filters = document.querySelectorAll('#filters input, #filters select, #filters [type="radio"]');

    filters.forEach(filter => {

        // Es la BARRA DE BÚSQUEDA (Texto)
        if (filter.id === 'query') {
            // Escuchamos cuando se baja una tecla
            filter.addEventListener('keydown', (event) => {
                // Solo buscamos si la tecla es ENTER
                if (event.key === 'Enter') {
                    event.preventDefault(); // Evita que se recargue la página si hay un form
                    performSearch();
                }
            });
        }

        // Son los OTROS FILTROS (Selects, Radio buttons, Fechas...)
        // Estos es mejor dejarlos con 'change' para que al hacer click se filtren solos.
        // (Si también quieres que estos esperen a un botón, avísame, pero lo estándar es que sean inmediatos).
        else {
            filter.addEventListener('change', performSearch);
        }
    });

    // Listener del botón limpiar
    const clearBtn = document.getElementById('clear-filters');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearFilters);
    }
}

// Función para manejar la carga inicial y el parámetro 'query' de la URL
function handleInitialLoad() {
    let urlParams = new URLSearchParams(window.location.search);
    const queryInputSidebar = document.getElementById('query'); //CAmpo lateral (Explore)
    const queryInputHeader = document.getElementById('search-query'); //Campo del header

    //Sincronizar el campo de búsqueda lateral con el parámetro 'query'
    let queryParam = urlParams.get('query');
    if (queryParam && queryParam.trim() !== '') {
        if(queryInputSidebar) {
            queryInputSidebar.value = queryParam;
        }
        if (queryInputHeader) {
            queryInputHeader.value = queryParam;
        }
    } else {
        if (queryInputSidebar && queryInputHeader) {
            queryInputSidebar.value = queryInputHeader.value;
        }
    }

    //Sincronizar el campo de advanced filter con los parámetros de la URL
    const advancedFIltersMAp = {
        'author': 'filter-author',
        'description': 'filter-description',
        'file': 'filter-file',
        'date': 'filter-date',
        'tags': 'filter-tags-nav'
    };

    for (const [paramName, elementId] of Object.entries(advancedFIltersMAp)) {
        let paramValue = urlParams.get(paramName);
        const element = document.getElementById(elementId);
        if ( paramValue && paramValue.trim() !== '' && element) {
            element.value = paramValue;
        }
    }

    // Ejecuta la búsqueda inicial con los valores actuales del formulario
    performSearch();
    console.log("Initial search executed");
}

// ------------------- Funciones Auxiliares -------------------

function formatDate(dateString) {
    const options = {day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: 'numeric'};
    const date = new Date(dateString);
    return date.toLocaleString('en-US', options);
}

function set_tag_as_query(tagName) {
    const queryInput = document.getElementById('query');
    queryInput.value = tagName.trim();
    // Llama directamente a la búsqueda
    performSearch();
}

function set_publication_type_as_query(publicationType) {
    const publicationTypeSelect = document.getElementById('publication_type');
    for (let i = 0; i < publicationTypeSelect.options.length; i++) {
        if (publicationTypeSelect.options[i].text === publicationType.trim()) {
            publicationTypeSelect.value = publicationTypeSelect.options[i].value;
            break;
        }
    }
    // Llama directamente a la búsqueda
    performSearch();
}

function clearFilters() {
    // Reset the search query
    let queryInput = document.querySelector('#query');
    queryInput.value = "";

    // Reset the publication type to its default value
    let publicationTypeSelect = document.querySelector('#publication_type');
    publicationTypeSelect.value = "any";

    // Reset the sorting option
    let sortingOptions = document.querySelectorAll('[name="sorting"]');
    sortingOptions.forEach(option => {
        // Marca 'newest' como seleccionado por defecto
        option.checked = option.value === "newest";
    });

    //Resetear los filtros avanzados del HEADER (base_template)
    document.getElementById('filter-author').value = '';
    document.getElementById('filter-description').value = '';
    document.getElementById('filter-file').value = '';
    document.getElementById('filter-date').value = '';
    const tagsInput = document.getElementById('filter-tags-nav');
    if (tagsInput) {
        tagsInput.value = '';
    }
    // Realizar una nueva búsqueda con los filtros reseteados
    performSearch();
}
