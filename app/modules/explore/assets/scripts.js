document.addEventListener('DOMContentLoaded', () => {
    // 1. Asignar listeners a los filtros (solo una vez)
    setupFilterListeners();
    
    // 2. Comprobar parámetros de URL y ejecutar la búsqueda inicial
    handleInitialLoad();
});

// Función central: Se encarga ÚNICAMENTE de ejecutar el FETCH y renderizar los resultados.
function performSearch() {
    
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
    // Selecciona todos los inputs (incluyendo #query), selects y radios dentro de #filters
    const filters = document.querySelectorAll('#filters input, #filters select, #filters [type="radio"]');

    filters.forEach(filter => {
        // Al detectar un cambio (evento 'input'), ejecuta la búsqueda
        filter.addEventListener('input', performSearch);
    });

    // Asignamos el listener del botón limpiar
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
}

// Función para manejar la carga inicial y el parámetro 'query' de la URL
function handleInitialLoad() {
    let urlParams = new URLSearchParams(window.location.search);
    let queryParam = urlParams.get('query');
    const queryInput = document.getElementById('query');

    if (queryParam && queryParam.trim() !== '') {
        queryInput.value = queryParam;
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

    // Realizar una nueva búsqueda con los filtros reseteados
    performSearch(); 
}