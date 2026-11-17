
import streamlit as st
import fitz
import re
import random
import time
from collections import Counter

# =========================================================
# EXAMFORGE - CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="ExamForge | Examination Suite",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background: #f5f6f8;
    color: #263244;
}
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}
.main-title {
    font-size: 38px;
    font-weight: 750;
    color: #263448;
    letter-spacing: -1px;
}
.subtitle {
    color: #778191;
    font-size: 15px;
    margin-bottom: 25px;
}
.feature-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 22px;
    min-height: 150px;
}
.feature-card h3 {
    color: #263448;
}
.feature-card p {
    color: #778191;
    font-size: 14px;
}
div.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid #d7dce3;
}
div.stButton > button[kind="primary"] {
    background: #344c69;
    color: white;
    border-color: #344c69;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION DATA
# =========================================================

DEFAULTS = {
    "navigation": "Dashboard",
    "question_bank": [],
    "generated_preview": [],
    "paper_preview": [],
    "quiz_questions": [],
    "quiz_answers": {},
    "quiz_started": False,
    "quiz_submitted": False,
    "quiz_score": 0,
    "quiz_start_time": None,
    "quiz_elapsed": 0,
    "quiz_id": 0,
    "paper_title": "ExamForge Practice Examination",
    "paper_marks": 1,
    "exam_attempts": 0
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# SAMPLE QUESTION BANK
# =========================================================

SAMPLE_QUESTIONS = [
    {
        "question": "Which language is widely used for Artificial Intelligence?",
        "options": ["Python", "HTML", "CSS", "SQL"],
        "answer": "Python",
        "explanation": "Python has many libraries for machine learning and AI.",
        "type": "Sample"
    },
    {
        "question": "Which data structure follows FIFO?",
        "options": ["Stack", "Queue", "Tree", "Graph"],
        "answer": "Queue",
        "explanation": "FIFO means First In, First Out.",
        "type": "Sample"
    },
    {
        "question": "Which language is used to query relational databases?",
        "options": ["SQL", "CSS", "HTML", "Python"],
        "answer": "SQL",
        "explanation": "SQL is used to manage and query relational databases.",
        "type": "Sample"
    },
    {
        "question": "What does CPU stand for?",
        "options": [
            "Central Processing Unit",
            "Computer Personal Unit",
            "Central Program Utility",
            "Control Processing User"
        ],
        "answer": "Central Processing Unit",
        "explanation": "CPU stands for Central Processing Unit.",
        "type": "Sample"
    },
    {
        "question": "Which data structure follows LIFO?",
        "options": ["Queue", "Stack", "Array", "Linked List"],
        "answer": "Stack",
        "explanation": "LIFO means Last In, First Out.",
        "type": "Sample"
    }
]


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_pdf_text(pdf_bytes):
    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    try:
        for page in document:
            pages.append(page.get_text("text"))
    finally:
        document.close()

    return "\n".join(pages)


# =========================================================
# TEXT CLEANING
# =========================================================

STOP_WORDS = {
    "the", "is", "are", "was", "were", "a", "an", "and",
    "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "it", "this", "that",
    "these", "those", "which", "who", "when", "where",
    "what", "how", "can", "could", "will", "would",
    "should", "has", "have", "had", "be", "been",
    "being", "their", "they", "them", "its", "into",
    "than", "then", "also", "such", "each", "more",
    "most", "some", "many", "any", "not", "all",
    "these", "those", "there", "here", "very", "much",
    "one", "two", "first", "second", "third", "following",
    "following", "example", "figure", "table", "chapter",
    "section", "using", "used", "use", "based", "called",
    "known", "defined", "definition", "following"
}


def clean_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    text = clean_text(text)

    sentences = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9])",
        text
    )

    cleaned = []

    for sentence in sentences:
        sentence = sentence.strip()

        if 7 <= len(sentence.split()) <= 65:
            cleaned.append(sentence)

    return cleaned


def get_words(text):
    words = re.findall(
        r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b",
        text
    )

    return [
        word for word in words
        if word.lower() not in STOP_WORDS
    ]


def unique_words(words):
    result = []
    seen = set()

    for word in words:
        key = word.lower()

        if key not in seen:
            seen.add(key)
            result.append(word)

    return result


# =========================================================
# DEFINITION DETECTION
# =========================================================

DEFINITION_PATTERNS = [
    r"^(.{2,65}?)\s+is defined as\s+(.{5,250})$",
    r"^(.{2,65}?)\s+refers to\s+(.{5,250})$",
    r"^(.{2,65}?)\s+is known as\s+(.{5,250})$",
    r"^(.{2,65}?)\s+means\s+(.{5,250})$",
    r"^(.{2,65}?)\s+is the\s+(.{5,250})$",
    r"^(.{2,65}?)\s+are the\s+(.{5,250})$"
]


def extract_definitions(sentences):
    definitions = []

    for sentence in sentences:
        sentence = sentence.strip(" .")

        for pattern in DEFINITION_PATTERNS:
            match = re.search(
                pattern,
                sentence,
                flags=re.IGNORECASE
            )

            if not match:
                continue

            term = match.group(1).strip(" ,:-")
            meaning = match.group(2).strip(" .")

            if len(term.split()) > 6:
                continue

            if len(meaning.split()) < 3:
                continue

            if len(term) < 3:
                continue

            definitions.append({
                "term": term,
                "meaning": meaning,
                "source": sentence
            })

            break

    return definitions


# =========================================================
# ABBREVIATION DETECTION
# =========================================================

def extract_abbreviations(text):
    patterns = [
        r"\b([A-Z][A-Za-z\s-]{3,60})\s*\(([A-Z]{2,10})\)",
        r"\b([A-Z]{2,10})\s*\(([A-Z][A-Za-z\s-]{3,60})\)"
    ]

    results = []

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            first = match.group(1).strip()
            second = match.group(2).strip()

            if second.isupper():
                full_form = first
                abbreviation = second
            else:
                abbreviation = first
                full_form = second

            if len(full_form.split()) <= 8:
                results.append({
                    "abbreviation": abbreviation,
                    "full_form": full_form
                })

    return results


# =========================================================
# RULE-BASED DISTRACTOR GENERATION
# =========================================================

def create_options(answer, candidates, count=3):
    candidates = unique_words(candidates)

    candidates = [
        word for word in candidates
        if word.lower() != answer.lower()
    ]

    # Prefer words of similar length.
    candidates.sort(
        key=lambda word: abs(len(word) - len(answer))
    )

    selected = candidates[:max(count * 3, count)]

    if len(selected) > count:
        selected = random.sample(selected, count)

    if len(selected) < count:
        return []

    options = selected + [answer]
    random.shuffle(options)

    return options


# =========================================================
# ADVANCED RULE-BASED MCQ GENERATOR
# =========================================================

def generate_mcqs(text, number_of_questions=10):

    sentences = split_sentences(text)

    if len(sentences) < 2:
        return []

    definitions = extract_definitions(sentences)
    abbreviations = extract_abbreviations(text)

    all_words = unique_words(get_words(text))

    questions = []
    used_questions = set()

    def add_question(question, answer, candidates, explanation, qtype):

        question_key = question.lower().strip()

        if question_key in used_questions:
            return

        options = create_options(
            answer,
            candidates
        )

        if len(options) != 4:
            return

        questions.append({
            "question": question,
            "options": options,
            "answer": answer,
            "explanation": explanation,
            "type": qtype
        })

        used_questions.add(question_key)

    # -----------------------------------------------------
    # TYPE 1: DEFINITION QUESTIONS
    # -----------------------------------------------------

    definition_terms = [
        item["term"] for item in definitions
    ]

    for item in definitions:

        if len(questions) >= number_of_questions:
            break

        answer = item["term"]

        if len(answer.split()) > 5:
            continue

        question = (
            "Which term is described by the following definition?\n\n"
            + item["meaning"]
        )

        add_question(
            question,
            answer,
            definition_terms,
            "This definition is taken from the uploaded document: "
            + item["source"],
            "Definition"
        )

    # -----------------------------------------------------
    # TYPE 2: ABBREVIATION QUESTIONS
    # -----------------------------------------------------

    abbreviation_options = [
        item["full_form"] for item in abbreviations
    ]

    for item in abbreviations:

        if len(questions) >= number_of_questions:
            break

        question = (
            "What is the full form of "
            + item["abbreviation"] + "?"
        )

        add_question(
            question,
            item["full_form"],
            abbreviation_options,
            "The abbreviation and its expansion were found "
            "together in the uploaded document.",
            "Abbreviation"
        )

    # -----------------------------------------------------
    # TYPE 3: FILL-IN-THE-BLANK QUESTIONS
    # -----------------------------------------------------

    word_frequency = Counter(
        word.lower() for word in get_words(text)
    )

    for sentence in sentences:

        if len(questions) >= number_of_questions:
            break

        words = get_words(sentence)

        if len(words) < 4:
            continue

        # Select a meaningful, relatively frequent term.
        ranked_words = sorted(
            unique_words(words),
            key=lambda word: (
                word_frequency[word.lower()],
                len(word)
            ),
            reverse=True
        )

        answer = None

        for word in ranked_words:
            if (
                len(word) >= 4
                and word.lower() not in STOP_WORDS
            ):
                answer = word
                break

        if not answer:
            continue

        # Avoid overly short or unhelpful sentences.
        if len(sentence.split()) < 8:
            continue

        blank_sentence = re.sub(
            r"\b" + re.escape(answer) + r"\b",
            "________",
            sentence,
            count=1,
            flags=re.IGNORECASE
        )

        question = (
            "Complete the statement:\n\n"
            + blank_sentence
        )

        add_question(
            question,
            answer,
            all_words,
            "The missing term appears in this sentence "
            "of the uploaded document:\n" + sentence,
            "Fill in the blank"
        )

    # -----------------------------------------------------
    # TYPE 4: IMPORTANT TERM QUESTIONS
    # -----------------------------------------------------

    if len(questions) < number_of_questions:

        # Use terms repeated in the document as candidates.
        frequent_terms = [
            word for word, frequency in word_frequency.most_common(30)
            if frequency >= 2 and len(word) >= 4
        ]

        for sentence in sentences:

            if len(questions) >= number_of_questions:
                break

            sentence_words = get_words(sentence)

            if len(sentence_words) < 5:
                continue

            # Select a repeated important word present in sentence.
            possible = [
                word for word in sentence_words
                if word.lower() in frequent_terms
            ]

            if not possible:
                continue

            answer = max(
                possible,
                key=lambda word: word_frequency[word.lower()]
            )

            blank_sentence = re.sub(
                r"\b" + re.escape(answer) + r"\b",
                "________",
                sentence,
                count=1,
                flags=re.IGNORECASE
            )

            question = (
                "Choose the correct term to complete the statement:\n\n"
                + blank_sentence
            )

            add_question(
                question,
                answer,
                frequent_terms,
                "The correct term is used in the original "
                "statement from the uploaded document.",
                "Important term"
            )

    return questions[:number_of_questions]


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 📝 ExamForge")
    st.caption("Examination Management Suite")
    st.divider()

    pages = [
        "Dashboard",
        "PDF to MCQs",
        "Question Paper Maker",
        "Quiz Simulator",
        "Question Bank",
        "About Project"
    ]

    selected_page = st.radio(
        "NAVIGATION",
        pages,
        key="navigation"
    )

    st.divider()
    st.caption("Learn • Practice • Evaluate")
    st.caption("Version 2.0")


# =========================================================
# DASHBOARD
# =========================================================

if selected_page == "Dashboard":

    st.markdown(
        '<div class="main-title">Welcome to ExamForge</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">A structured platform for '
        'question generation, paper creation and exam practice.</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Question Bank",
        len(st.session_state.question_bank)
    )

    c2.metric(
        "Generated MCQs",
        len(st.session_state.generated_preview)
    )

    c3.metric(
        "Exam Attempts",
        st.session_state.exam_attempts
    )

    st.markdown("### Explore ExamForge")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
        <h3>📄 PDF to MCQs</h3>
        <p>Extract academic content and generate
        rule-based multiple-choice questions.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Open PDF Generator", use_container_width=True):
            st.session_state.navigation = "PDF to MCQs"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="feature-card">
        <h3>📚 Question Paper Maker</h3>
        <p>Create practice papers using questions
        from your question bank.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Create Question Paper", use_container_width=True):
            st.session_state.navigation = "Question Paper Maker"
            st.rerun()

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("""
        <div class="feature-card">
        <h3>⏱️ Quiz Simulator</h3>
        <p>Attempt questions, submit answers
        and evaluate your performance.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Start Quiz", use_container_width=True):
            st.session_state.navigation = "Quiz Simulator"
            st.rerun()

    with col4:
        st.markdown("""
        <div class="feature-card">
        <h3>🗂️ Question Bank</h3>
        <p>View questions generated during
        your current session.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("View Question Bank", use_container_width=True):
            st.session_state.navigation = "Question Bank"
            st.rerun()


# =========================================================
# PDF TO MCQS
# =========================================================

elif selected_page == "PDF to MCQs":

    st.title("PDF to MCQ Generator")

    st.write(
        "Upload an academic PDF to extract its text "
        "and generate practice questions."
    )

    st.info(
        "Generation methods: definitions, abbreviations, "
        "fill-in-the-blanks and important terms."
    )

    uploaded_file = st.file_uploader(
        "Upload your PDF",
        type=["pdf"]
    )

    question_count = st.slider(
        "Number of questions",
        5, 30, 10
    )

    if st.button("Generate MCQs", type="primary"):

        # Clear old results before generating new ones.
        st.session_state.generated_preview = []

        if uploaded_file is None:
            st.warning("Please upload a PDF first.")

        else:
            try:
                with st.spinner(
                    "Extracting content and analysing the PDF..."
                ):

                    pdf_bytes = uploaded_file.getvalue()

                    extracted_text = extract_pdf_text(pdf_bytes)

                    if len(extracted_text.strip()) < 100:
                        st.warning(
                            "This PDF has insufficient extractable text. "
                            "It may be scanned or image-based."
                        )

                    else:
                        generated = generate_mcqs(
                            extracted_text,
                            question_count
                        )

                        st.session_state.generated_preview = generated

                        if generated:
                            st.session_state.question_bank.extend(
                                generated
                            )

                            st.success(
                                f"Generated {len(generated)} questions!"
                            )

                        else:
                            st.warning(
                                "No suitable questions could be generated. "
                                "Try a PDF with more readable academic content "
                                "and clear definitions."
                            )

            except Exception as error:
                st.error(
                    f"PDF processing error: {error}"
                )

    if st.session_state.generated_preview:

        st.divider()
        st.subheader("Generated Questions")

        for index, question in enumerate(
            st.session_state.generated_preview,
            start=1
        ):

            with st.expander(
                f"Question {index} | {question['type']}"
            ):

                st.write(question["question"])

                for option_index, option in enumerate(
                    question["options"]
                ):
                    st.write(
                        f"{chr(65 + option_index)}. {option}"
                    )

                st.success(
                    "Correct answer: " + question["answer"]
                )

                st.caption(question["explanation"])

        download_text = []

        for index, question in enumerate(
            st.session_state.generated_preview,
            start=1
        ):
            download_text.append(
                f"Q{index}. {question['question']}"
            )

            for option_index, option in enumerate(
                question["options"]
            ):
                download_text.append(
                    f"{chr(65 + option_index)}. {option}"
                )

            download_text.append(
                "Answer: " + question["answer"]
            )

            download_text.append("")

        st.download_button(
            "Download Generated Questions",
            "\n".join(download_text),
            file_name="ExamForge_MCQs.txt",
            mime="text/plain"
        )


# =========================================================
# QUESTION PAPER MAKER
# =========================================================

elif selected_page == "Question Paper Maker":

    st.title("Question Paper Maker")

    questions = st.session_state.question_bank

    if not questions:
        st.info(
            "Your question bank is empty. Generate MCQs "
            "or load sample questions first."
        )

    else:
        st.metric("Available Questions", len(questions))

        title = st.text_input(
            "Question paper title",
            "ExamForge Practice Examination"
        )

        count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=len(questions),
            value=min(5, len(questions))
        )

        marks = st.number_input(
            "Marks per question",
            min_value=1,
            max_value=10,
            value=1
        )

        if st.button("Generate Question Paper", type="primary"):

            st.session_state.paper_preview = random.sample(
                questions,
                int(count)
            )

            st.session_state.paper_title = title
            st.session_state.paper_marks = marks

        if st.session_state.paper_preview:

            st.divider()

            st.subheader(st.session_state.paper_title)

            paper = [
                st.session_state.paper_title,
                "=" * 45,
                f"Total Questions: {len(st.session_state.paper_preview)}",
                f"Total Marks: {len(st.session_state.paper_preview) * st.session_state.paper_marks}",
                ""
            ]

            for index, question in enumerate(
                st.session_state.paper_preview,
                start=1
            ):

                st.markdown(
                    f"**Q{index}. {question['question']}**"
                )

                paper.append(
                    f"Q{index}. {question['question']}"
                )

                for option_index, option in enumerate(
                    question["options"]
                ):
                    label = chr(65 + option_index)
                    st.write(f"{label}. {option}")
                    paper.append(f"{label}. {option}")

                paper.append("")

            st.download_button(
                "Download Question Paper",
                "\n".join(paper),
                file_name="ExamForge_Question_Paper.txt",
                mime="text/plain"
            )


# =========================================================
# QUIZ SIMULATOR
# =========================================================

elif selected_page == "Quiz Simulator":

    st.title("Quiz & Exam Simulator")

    if not st.session_state.quiz_started:

        st.markdown("### Examination Instructions")

        st.write("1. Select one answer for every question.")
        st.write("2. Each correct answer carries one mark.")
        st.write("3. Submit your answers to view your result.")
        st.write("4. Your attempt is temporary.")

        source = st.radio(
            "Choose question source",
            ["Question Bank", "Sample Questions"]
        )

        available = (
            st.session_state.question_bank
            if source == "Question Bank"
            else SAMPLE_QUESTIONS
        )

        if not available:
            st.warning(
                "Your question bank is empty. Generate questions "
                "or choose Sample Questions."
            )

        else:
            count = st.number_input(
                "Number of questions",
                min_value=1,
                max_value=len(available),
                value=min(5, len(available))
            )

            if st.button("Start Examination", type="primary"):

                st.session_state.quiz_questions = random.sample(
                    available,
                    int(count)
                )

                st.session_state.quiz_answers = {}
                st.session_state.quiz_started = True
                st.session_state.quiz_submitted = False
                st.session_state.quiz_start_time = time.time()
                st.session_state.quiz_id += 1

                st.rerun()

    elif (
        st.session_state.quiz_started
        and not st.session_state.quiz_submitted
    ):

        questions = st.session_state.quiz_questions

        st.info(
            f"Total Questions: {len(questions)} | "
            f"Total Marks: {len(questions)}"
        )

        with st.form(
            key=f"quiz_form_{st.session_state.quiz_id}"
        ):

            answers = {}

            for index, question in enumerate(questions):

                st.markdown(
                    f"**Q{index + 1}. {question['question']}**"
                )

                answers[index] = st.radio(
                    "Select your answer",
                    question["options"],
                    index=None,
                    key=f"answer_{st.session_state.quiz_id}_{index}",
                    label_visibility="collapsed"
                )

                st.divider()

            submitted = st.form_submit_button(
                "Submit Examination",
                type="primary",
                use_container_width=True
            )

            if submitted:

                score = sum(
                    1 for index, question in enumerate(questions)
                    if answers.get(index) == question["answer"]
                )

                st.session_state.quiz_answers = answers
                st.session_state.quiz_score = score
                st.session_state.quiz_submitted = True

                st.session_state.quiz_elapsed = (
                    time.time() - st.session_state.quiz_start_time
                )

                st.session_state.exam_attempts += 1

                st.rerun()

        if st.button("Cancel Examination"):
            st.session_state.quiz_started = False
            st.session_state.quiz_questions = []
            st.session_state.quiz_answers = {}
            st.rerun()

    elif st.session_state.quiz_submitted:

        questions = st.session_state.quiz_questions
        score = st.session_state.quiz_score
        total = len(questions)

        percentage = score / total * 100 if total else 0

        st.success("Examination submitted successfully!")

        c1, c2, c3 = st.columns(3)

        c1.metric("Score", f"{score}/{total}")
        c2.metric("Percentage", f"{percentage:.1f}%")
        c3.metric(
            "Time Taken",
            f"{st.session_state.quiz_elapsed / 60:.1f} min"
        )

        if percentage >= 80:
            st.success("Excellent performance!")

        elif percentage >= 50:
            st.info("Good effort. Keep practising!")

        else:
            st.warning("Keep learning and try again.")

        st.divider()
        st.subheader("Answer Review")

        for index, question in enumerate(questions):

            user_answer = st.session_state.quiz_answers.get(index)

            st.markdown(
                f"**Q{index + 1}. {question['question']}**"
            )

            st.write(
                "Your answer: " + (user_answer or "Not answered")
            )

            st.write(
                "Correct answer: " + question["answer"]
            )

            if user_answer == question["answer"]:
                st.success("Correct")
            else:
                st.error("Incorrect")

            st.caption(question["explanation"])
            st.divider()

        if st.button("Start New Examination", type="primary"):

            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = False
            st.session_state.quiz_questions = []
            st.session_state.quiz_answers = {}

            st.rerun()


# =========================================================
# QUESTION BANK
# =========================================================

elif selected_page == "Question Bank":

    st.title("Question Bank")

    questions = st.session_state.question_bank

    st.metric("Total Questions", len(questions))

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Load Sample Questions"):
            st.session_state.question_bank.extend(
                SAMPLE_QUESTIONS.copy()
            )
            st.success("Sample questions added.")
            st.rerun()

    with col2:
        if st.button("Clear Question Bank"):
            st.session_state.question_bank = []
            st.session_state.generated_preview = []
            st.success("Question bank cleared.")
            st.rerun()

    st.divider()

    if questions:

        for index, question in enumerate(questions, start=1):

            with st.expander(f"Question {index}"):

                st.write(question["question"])

                for option_index, option in enumerate(
                    question["options"]
                ):
                    st.write(
                        f"{chr(65 + option_index)}. {option}"
                    )

                st.caption(
                    f"Answer: {question['answer']}"
                )

                st.caption(
                    f"Type: {question.get('type', 'General')}"
                )

    else:
        st.info("No questions available yet.")


# =========================================================
# ABOUT PROJECT
# =========================================================

elif selected_page == "About Project":

    st.title("About ExamForge")

    st.write(
        "ExamForge is a Python-based examination management "
        "website designed to simplify question preparation "
        "and student practice."
    )

    st.subheader("Core Modules")

    st.markdown("""
    - **PDF to MCQ Generator:** Extracts academic PDF text
      and generates questions using Python rules.
    - **Question Paper Maker:** Creates practice papers
      from the available question bank.
    - **Quiz Simulator:** Allows students to attempt
      examinations and view their performance.
    - **Question Bank:** Organises questions during
      the current application session.
    """)

    st.subheader("Question Generation Methods")

    st.markdown("""
    - Definition pattern detection
    - Abbreviation extraction
    - Fill-in-the-blank generation
    - Repeated important-term detection
    - Rule-based distractor selection
    """)

    st.subheader("Technology Stack")

    st.markdown("""
    - Python
    - Streamlit
    - PyMuPDF
    - Regular expressions
    - Rule-based text processing
    """)

    st.subheader("Data and Privacy")

    st.write(
        "ExamForge does not use a database. Uploaded PDF content, "
        "generated questions and quiz attempts are handled in "
        "temporary application session memory. The application "
        "does not intentionally save these materials permanently."
    )

    st.caption(
        "Hosting providers may process application traffic "
        "and temporary data according to their own policies."
    )

    st.divider()
    st.caption("ExamForge | Version 2.0")

