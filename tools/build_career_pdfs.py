"""Build the three canonical, evidence-backed ATS resumes.

The generated documents intentionally use only plain text, one column, standard
headings, and ASCII separators so they remain easy for ATS parsers to read.
"""

from html import escape
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "resumes"
OUT.mkdir(exist_ok=True)

CONTACT = (
    "Trivandrum, Kerala, India | +91 7994454919 | praksediting5@gmail.com | "
    "linkedin.com/in/prak05"
)

CSS = """
@page { size: A4; margin: 11mm 14mm 10mm; }
* { box-sizing: border-box; }
body {
  font-family: Arial, Helvetica, sans-serif;
  color: #222;
  font-size: 10pt;
  line-height: 1.16;
  margin: 0;
}
header { border-bottom: 1px solid #222; padding-bottom: 5px; margin-bottom: 6px; }
h1 { font-size: 18pt; letter-spacing: .02em; margin: 0 0 2px; }
h2 {
  border-bottom: 1px solid #777;
  color: #333;
  font-size: 9.5pt;
  letter-spacing: .06em;
  margin: 7px 0 3px;
  padding-bottom: 2px;
}
h3 { font-size: 10pt; margin: 4px 0 1px; }
p { margin: 2px 0 3px; }
ul { margin: 1px 0 3px 15px; padding: 0; }
li { margin: 1px 0; }
strong { color: #111; }
.target { color: #444; font-size: 9.5pt; }
.dates { color: #555; font-weight: normal; }
.footer { color: #666; font-size: 7.5pt; margin-top: 5px; }
"""

TRACKS = {
    "Software_Engineering": {
        "filename": "ATS_Resume_Software_Engineering_Prakhar_Sharma",
        "label": "SOFTWARE ENGINEERING",
        "summary": (
            "Computer Science and Engineering student with hands-on experience building "
            "Python and Java applications, REST services, document-processing workflows, "
            "and user-facing prototypes. Comfortable moving from requirements to tested "
            "implementation with Git, SQL, and cloud-aware design."
        ),
        "skills": [
            ("Languages", "Python, Java, JavaScript, SQL"),
            ("Backend and web", "FastAPI, REST APIs, Streamlit, HTML, CSS"),
            ("Data and AI", "RAG, NLP, scikit-learn, TensorFlow, PyTorch, Jupyter"),
            ("Engineering", "Git, Linux, Docker, JDBC, Oracle, testing"),
        ],
        "experience": [
            (
                "KSERC regulatory automation project",
                "Project / internship work | 2026",
                [
                    "Worked on PDF ingestion, table extraction, regulation retrieval, calculations, validation, and document export for an electricity-regulation analysis workflow.",
                    "Implemented backend and local/cloud execution components with Python, storage abstractions, and Terraform within the project scope.",
                ],
            ),
            (
                "VirtuNexa",
                "Android Developer Intern | Dec 2024 - Jan 2025",
                [
                    "Developed and tested Android application features using Java and Kotlin.",
                    "Practised UI implementation, debugging, and maintainable mobile code within an internship team.",
                ],
            ),
            (
                "Innovate Intern, Edunet Foundation, EISystems Technologies, A.N.D. Intern",
                "Cloud, AI, web, and data internships | 2024",
                [
                    "Completed guided work across Google Cloud, AI, cloud/front-end development, data science, REST APIs, and security concepts.",
                ],
            ),
        ],
        "projects": [
            (
                "MediScribe",
                "FastAPI and Streamlit medical-information workflow using RAG, PubMed retrieval, citations, and tests.",
            ),
            (
                "LinkedIn Indo",
                "Local-first Python drafting assistant with validation, revisions, and a Terraform-defined AWS architecture.",
            ),
            (
                "Smart Irrigation",
                "Python and Streamlit agriculture project using scikit-learn MultiOutputClassifier with RandomForest.",
            ),
            (
                "KNB Bank Management System",
                "Java, JDBC, and Oracle application covering account, transaction, approval, and audit workflows.",
            ),
        ],
    },
    "AI_ML_Data": {
        "filename": "ATS_Resume_AI_ML_Data_Prakhar_Sharma",
        "label": "AI / ML / DATA",
        "summary": (
            "Computer Science and Engineering student focused on practical machine "
            "learning, retrieval-augmented generation, data workflows, and responsible "
            "AI prototypes. Builds explainable, testable applications with Python and "
            "clear evidence trails from source data to user-facing output."
        ),
        "skills": [
            ("Programming", "Python, Java, SQL, JavaScript"),
            ("Machine learning", "scikit-learn, MultiOutputClassifier, RandomForest, TensorFlow, PyTorch"),
            ("AI and retrieval", "RAG, NLP, PubMed retrieval, embeddings, evaluation"),
            ("Applications", "FastAPI, Streamlit, Jupyter, REST APIs, Git, Linux, testing"),
        ],
        "experience": [
            (
                "KSERC regulatory automation project",
                "Project / internship work | 2026",
                [
                    "Worked on extracting tables from regulatory PDFs, retrieving relevant regulations, applying calculation logic, and presenting validation-ready outputs.",
                    "Contributed Python backend and document-processing components within the project scope.",
                ],
            ),
            (
                "AI and data internships",
                "Edunet Foundation / IBM SkillsBuild / A.N.D. Intern | 2024",
                [
                    "Completed guided AI, data-science, visualization, and model-focused work through Edunet Foundation, IBM SkillsBuild, and A.N.D. Intern.",
                ],
            ),
            (
                "VirtuNexa",
                "Android Developer Intern | Dec 2024 - Jan 2025",
                [
                    "Developed and tested Android features with Java and Kotlin, building practical software and debugging experience.",
                ],
            ),
        ],
        "projects": [
            (
                "MediScribe",
                "FastAPI and Streamlit medical-information application with RAG, PubMed retrieval, citations, and tests.",
            ),
            (
                "MedBuddy",
                "Medical AI prototype exploring ingestion, chunking, retrieval, re-ranking, citations, and evaluation.",
            ),
            (
                "Smart Irrigation",
                "Python and Streamlit project using scikit-learn MultiOutputClassifier with RandomForest for irrigation recommendations.",
            ),
            (
                "Fasal Saarthi",
                "Agriculture project using IBM Watsonx.ai AutoAI and IBM Cloud for data-driven crop recommendations.",
            ),
        ],
    },
    "AWS_Cloud": {
        "filename": "ATS_Resume_AWS_Cloud_Prakhar_Sharma",
        "label": "AWS / CLOUD ENGINEERING",
        "summary": (
            "Computer Science and Engineering student with project experience in AWS "
            "serverless architecture, Terraform, Google Cloud, IBM Cloud, backend "
            "services, and local-first development. Designs cloud-aware systems while "
            "keeping a runnable local path and documenting infrastructure clearly."
        ),
        "skills": [
            ("Cloud", "AWS Lambda, API Gateway, DynamoDB, Cognito, S3, Google Cloud, IBM Cloud"),
            ("Infrastructure", "Terraform, IAM concepts, Docker, Linux, local/cloud configuration"),
            ("Backend", "Python, FastAPI, REST APIs, Java, JDBC, SQL"),
            ("Application tools", "Git, Streamlit, testing, document processing, RAG"),
        ],
        "experience": [
            (
                "KSERC regulatory automation project",
                "Project / internship work | 2026",
                [
                    "Contributed backend, PDF extraction, retrieval, validation, and document-export work for a regulatory analysis project.",
                    "Added local/cloud configuration and Terraform components within the project scope.",
                ],
            ),
            (
                "Innovate Intern",
                "Google Cloud Intern | 2024",
                [
                    "Completed a Google Cloud-focused internship project covering cloud computing and securing AI/ML workloads on Google Cloud.",
                ],
            ),
            (
                "Edunet Foundation / EISystems Technologies",
                "Cloud and front-end internship work | 2024",
                [
                    "Completed guided cloud, front-end, API, and security-oriented work through internship programs.",
                ],
            ),
        ],
        "projects": [
            (
                "LinkedIn Indo",
                "Terraform-defined AWS architecture using API Gateway, Lambda, DynamoDB, and Cognito; AWS stack is documented as project work and is not claimed as active deployment.",
            ),
            (
                "KSERC regulatory automation",
                "Cloud-aware Python workflow for PDF/table extraction, regulation retrieval, calculations, validation, and exports.",
            ),
            (
                "Fasal Saarthi",
                "IBM Watsonx.ai AutoAI and IBM Cloud agriculture project for data-driven crop recommendations.",
            ),
            (
                "MediScribe",
                "FastAPI and Streamlit application combining RAG, PubMed retrieval, citations, and tests.",
            ),
        ],
    },
}


def _text(value: str) -> str:
    """Escape text and normalize non-ASCII punctuation for ATS-safe output."""
    value = value.replace("–", "-").replace("—", "-").replace("’", "'")
    return escape(value, quote=False)


def _section(title: str) -> str:
    return f"<h2>{_text(title)}</h2>"


def _bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _header(track: dict) -> str:
    return (
        "<header><h1>Prakhar Sharma</h1>"
        f"<div class='target'>{_text(track['label'])}</div>"
        f"<p>{_text(CONTACT)}</p></header>"
    )


def resume_html(track_name: str) -> str:
    """Return one-column HTML for a canonical track-specific resume."""
    track = TRACKS[track_name]
    skills = "".join(
        f"<p><strong>{_text(group)}:</strong> {_text(items)}</p>"
        for group, items in track["skills"]
    )
    experience = "".join(
        f"<h3>{_text(role)} <span class='dates'>| {_text(dates)}</span></h3>"
        + _bullets(bullets)
        for role, dates, bullets in track["experience"]
    )
    projects = "".join(
        f"<p><strong>{_text(name)}:</strong> {_text(description)}</p>"
        for name, description in track["projects"]
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>"
        + _header(track)
        + _section("SUMMARY")
        + f"<p>{_text(track['summary'])}</p>"
        + _section("SKILLS")
        + skills
        + _section("EXPERIENCE")
        + experience
        + _section("SELECTED PROJECTS")
        + projects
        + _section("EDUCATION")
        + "<p><strong>B.Tech, Computer Science and Engineering</strong> - "
        "Rajadhani Institute of Engineering and Technology, Kerala | Expected 2027</p>"
        + _section("LEADERSHIP")
        + _bullets(
            [
                "Founder, Vidya Sadhnam - hosted student workshops on Linux, GitHub, cloud, AI, and data.",
                "MuLearn Alumni Cell Lead - supported student onboarding, partner communication, and community events.",
            ]
        )
        + "<p class='footer'>ATS format: one column, standard headings, plain text separators, no graphics or tables.</p>"
        + "</body></html>"
    )


def resume_markdown(track_name: str) -> str:
    """Return the editable, evidence-backed Markdown source for a resume."""
    track = TRACKS[track_name]
    lines = [
        "# Prakhar Sharma",
        f"**{track['label']}**",
        CONTACT,
        "",
        "## Summary",
        track["summary"],
        "",
        "## Skills",
    ]
    lines.extend(f"- **{group}:** {items}" for group, items in track["skills"])
    lines.extend(["", "## Experience"])
    for role, dates, bullets in track["experience"]:
        lines.append(f"### {role} | {dates}")
        lines.extend(f"- {item}" for item in bullets)
    lines.extend(["", "## Selected Projects"])
    lines.extend(f"- **{name}:** {description}" for name, description in track["projects"])
    lines.extend(
        [
            "",
            "## Education",
            "B.Tech, Computer Science and Engineering - Rajadhani Institute of Engineering and Technology, Kerala | Expected 2027",
            "",
            "## Leadership",
            "- Founder, Vidya Sadhnam - hosted student workshops on Linux, GitHub, cloud, AI, and data.",
            "- MuLearn Alumni Cell Lead - supported student onboarding, partner communication, and community events.",
            "",
            "## ATS notes",
            "One-column, one-page layout with standard headings and ASCII-safe separators. Claims are limited to the local evidence set reviewed 2026-11-03.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    for track_name, track in TRACKS.items():
        stem = track["filename"]
        html = OUT / f"{stem}.html"
        pdf = OUT / f"{stem}.pdf"
        markdown = OUT / f"{stem}.md"
        html.write_text(resume_html(track_name), encoding="utf-8")
        markdown.write_text(resume_markdown(track_name), encoding="utf-8")
        subprocess.run(
            [
                "google-chrome",
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf.resolve()}",
                html.resolve().as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        html.unlink()


if __name__ == "__main__":
    main()
