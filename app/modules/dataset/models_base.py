from enum import Enum

from app import db


class PublicationType(Enum):
    NONE = "none"
    ANNOTATION_COLLECTION = "annotationcollection"
    BOOK = "book"
    BOOK_SECTION = "section"
    CONFERENCE_PAPER = "conferencepaper"
    DATA_MANAGEMENT_PLAN = "datamanagementplan"
    JOURNAL_ARTICLE = "article"
    PATENT = "patent"
    PREPRINT = "preprint"
    PROJECT_DELIVERABLE = "deliverable"
    PROJECT_MILESTONE = "milestone"
    PROPOSAL = "proposal"
    REPORT = "report"
    SOFTWARE_DOCUMENTATION = "softwaredocumentation"
    TAXONOMIC_TREATMENT = "taxonomictreatment"
    TECHNICAL_NOTE = "technicalnote"
    THESIS = "thesis"
    WORKING_PAPER = "workingpaper"
    OTHER = "other"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    affiliation = db.Column(db.String(120))
    orcid = db.Column(db.String(120))
    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"))
    fm_meta_data_id = db.Column(db.Integer, db.ForeignKey("fm_meta_data.id"))

    def to_dict(self):
        return {"name": self.name, "affiliation": self.affiliation, "orcid": self.orcid}
