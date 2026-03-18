"""Generate a research paper PDF using fpdf2 with proper alignment."""
from fpdf import FPDF


class ResearchPaper(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Times", "I", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 6, "Two-Stage CLIP Re-Ranking with VLM-Augmented Hybrid Search", align="C")
            self.ln(6)
            self.set_draw_color(200, 200, 200)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(8)
            self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Times", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, num, title):
        self.ln(6)
        self.set_font("Times", "B", 14)
        self.set_text_color(0, 0, 0)
        label = f"{num}. {title}" if num else title
        self.cell(0, 8, label, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def sub_title(self, num, title):
        self.ln(3)
        self.set_font("Times", "B", 12)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, f"{num} {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def body_text(self, text):
        self.set_font("Times", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def draft_note(self, text):
        self.set_font("Times", "I", 10)
        self.set_text_color(120, 120, 120)
        self.multi_cell(0, 6, text)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def bullet(self, text, indent=10):
        """Bullet point with proper wrapped-line indentation."""
        old_margin = self.l_margin
        bullet_x = old_margin + indent
        text_x = bullet_x + 6
        # Print the dash
        self.set_font("Times", "", 11)
        self.set_x(bullet_x)
        self.cell(6, 5.5, "-")
        # Temporarily shift left margin so multi_cell wraps aligned
        self.set_left_margin(text_x)
        self.set_x(text_x)
        self.multi_cell(self.w - text_x - self.r_margin, 5.5, text)
        self.set_left_margin(old_margin)
        self.ln(1)

    def numbered_item(self, num, text, indent=10):
        """Numbered item with proper wrapped-line indentation."""
        old_margin = self.l_margin
        num_x = old_margin + indent
        text_x = num_x + 8
        self.set_font("Times", "", 11)
        self.set_x(num_x)
        self.cell(8, 5.5, f"{num}.")
        self.set_left_margin(text_x)
        self.set_x(text_x)
        self.multi_cell(self.w - text_x - self.r_margin, 5.5, text)
        self.set_left_margin(old_margin)
        self.ln(1)

    def bold_bullet(self, label, text, indent=10):
        """Bold-label bullet with proper wrapped-line indentation."""
        old_margin = self.l_margin
        bullet_x = old_margin + indent
        text_start = bullet_x + 6
        self.set_font("Times", "", 11)
        self.set_x(bullet_x)
        self.cell(6, 5.5, "-")
        # Print the bold label inline
        self.set_font("Times", "B", 11)
        label_text = f"{label}: "
        label_w = self.get_string_width(label_text)
        self.cell(label_w, 5.5, label_text)
        # Now print the rest as multi_cell with proper margin
        content_x = text_start  # wrap point for subsequent lines
        current_x = self.get_x()
        self.set_left_margin(content_x)
        self.set_font("Times", "", 11)
        self.multi_cell(self.w - current_x - self.r_margin, 5.5, text)
        self.set_left_margin(old_margin)
        self.ln(1)

    def code_block(self, text):
        self.set_font("Courier", "", 9.5)
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(210, 210, 210)
        x = self.l_margin
        y = self.get_y()
        lines = text.strip().split("\n")
        line_h = 5
        padding = 4
        block_h = len(lines) * line_h + padding * 2
        block_w = self.w - self.l_margin - self.r_margin
        self.rect(x, y, block_w, block_h, style="DF")
        self.set_xy(x + padding, y + padding)
        for i, line in enumerate(lines):
            self.set_x(x + padding)
            self.cell(block_w - padding * 2, line_h, line)
            if i < len(lines) - 1:
                self.ln(line_h)
        self.set_y(y + block_h + 3)
        self.ln(2)

    def add_table(self, headers, rows, col_widths=None):
        avail = self.w - self.l_margin - self.r_margin
        if col_widths is None:
            col_widths = [avail / len(headers)] * len(headers)

        row_h = 7
        # Header
        self.set_font("Times", "B", 10)
        self.set_fill_color(235, 235, 235)
        self.set_draw_color(160, 160, 160)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Times", "", 10)
        for row in rows:
            # Calculate needed height
            max_lines = 1
            for i, cell in enumerate(row):
                cw = col_widths[i] - 4  # padding
                if cw > 0:
                    text_w = self.get_string_width(cell)
                    lines_needed = max(1, int(text_w / cw) + 1)
                    max_lines = max(max_lines, lines_needed)
            rh = max(row_h, max_lines * 5.5 + 2)

            y_start = self.get_y()
            x_start = self.get_x()

            for i, cell in enumerate(row):
                x_cell = x_start + sum(col_widths[:i])
                # Draw cell border
                self.rect(x_cell, y_start, col_widths[i], rh)
                # Write text inside
                self.set_xy(x_cell + 2, y_start + 1.5)
                old_margin = self.l_margin
                self.set_left_margin(x_cell + 2)
                self.multi_cell(col_widths[i] - 4, 5, cell)
                self.set_left_margin(old_margin)

            self.set_xy(x_start, y_start + rh)
        self.ln(4)


# ============================================================
# BUILD THE PDF
# ============================================================
pdf = ResearchPaper()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.set_margins(25, 25, 25)

# ===== TITLE PAGE =====
pdf.add_page()
pdf.ln(40)
pdf.set_font("Times", "B", 22)
pdf.multi_cell(0, 11, "Two-Stage CLIP Re-Ranking with\nVLM-Augmented Hybrid Search for\nScalable Personal Image Retrieval", align="C")
pdf.ln(20)
pdf.set_draw_color(60, 60, 60)
pdf.line(65, pdf.get_y(), pdf.w - 65, pdf.get_y())
pdf.ln(20)
pdf.set_font("Times", "", 14)
pdf.cell(0, 9, "Aryan Marthak", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("Times", "I", 12)
pdf.cell(0, 8, "B.Tech, Final Year Major Project", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.cell(0, 8, "March 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(30)
pdf.set_font("Times", "I", 11)
pdf.set_text_color(130, 130, 130)
pdf.cell(0, 8, "Draft Version - Work in Progress", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(0, 0, 0)

# ===== ABSTRACT =====
pdf.add_page()
pdf.section_title("", "Abstract")
pdf.draft_note("[To be written after results are finalized.]")
pdf.body_text(
    "Personal image collections are growing rapidly, but current search methods still rely on manual browsing or "
    "simple filename matching. This paper presents an AI-powered image retrieval system that combines a two-stage "
    "CLIP-based search (global recall followed by local crop re-ranking) with a hybrid deep search that fuses BM25 "
    "keyword matching over VLM-generated descriptions with CLIP semantic embeddings. The system also integrates face "
    "detection, DBSCAN-based face clustering, query expansion, and temperature-based score calibration. We evaluate "
    "the pipeline against single-stage baselines on a personal photo collection and report Precision@K, mAP, and "
    "latency. Early observations suggest that the two-stage approach and hybrid scoring appear to improve retrieval "
    "precision without exceeding acceptable latency limits."
)

# ===== 1. INTRODUCTION =====
pdf.section_title("1", "Introduction")

pdf.sub_title("1.1", "Background")
pdf.body_text(
    "The average smartphone user accumulates thousands of photos each year. Family gatherings, vacations, food, "
    "documents, random screenshots. Finding a specific image when you need it is still surprisingly painful. You "
    "either scroll endlessly, or maybe try searching by date and hope you remember when the photo was taken."
)
pdf.body_text(
    "Cloud services like Google Photos and Apple Photos solve this with proprietary machine learning, but those "
    "solutions are closed-source, require uploading personal data to third-party servers, and offer no transparency "
    "into how search actually works. For users who care about privacy, or for small organizations that want "
    "on-premise search, there is a real gap."
)
pdf.body_text(
    "The deeper technical problem is that most retrieval systems encode an entire image into a single embedding "
    "vector. This captures the general feel of the photo but tends to miss fine-grained details: a logo on a shirt, "
    "a pet in the corner of the frame, or a specific book on a shelf. A user searching for \"red umbrella\" might "
    "get back photos of red cars and red buildings because the global embedding picks up redness without "
    "understanding spatial context."
)

pdf.sub_title("1.2", "Problem Statement")
pdf.body_text(
    "Given a personal image collection with no labels and variable quality, and a free-text query from an impatient "
    "user, the goal is to return a ranked list of relevant images with calibrated confidence scores, in under 5 seconds."
)
pdf.body_text("The constraints are real:")
pdf.bullet("No annotations exist. Nobody tags their holiday photos.")
pdf.bullet("Image quality varies wildly, from professional DSLR shots to blurry phone snaps.")
pdf.bullet("Users expect fast responses. Even 10 seconds feels too long for a search.")
pdf.bullet("The system should run on consumer hardware, not a cloud GPU cluster.")

pdf.sub_title("1.3", "Research Questions")
pdf.bold_bullet("RQ1", "Does local crop re-ranking significantly improve Precision@K compared to global-only CLIP retrieval?")
pdf.bold_bullet("RQ2", "Does a BM25 + CLIP hybrid approach on VLM descriptions outperform either modality used alone?")
pdf.bold_bullet("RQ3", "How does the weight ratio between global/local scores and BM25/CLIP scores affect the tradeoff between precision and query speed?")
pdf.bold_bullet("RQ4", "Can DBSCAN-based face clustering provide usable person-based search in uncurated personal collections?")

pdf.sub_title("1.4", "Contributions")
pdf.numbered_item(1, "A two-stage search pipeline combining CLIP ViT-L-14 global recall with local crop re-ranking (5 crops per image).")
pdf.numbered_item(2, "A hybrid deep search fusing BM25 keyword matching on VLM descriptions with CLIP semantic similarity.")
pdf.numbered_item(3, "Integrated face detection and clustering using DeepFace + DBSCAN for person-based search.")
pdf.numbered_item(4, "A fully deployable open-source system (FastAPI, React, Qdrant, PostgreSQL).")
pdf.numbered_item(5, "Ablation studies measuring the contribution of each pipeline component.")

pdf.sub_title("1.5", "Paper Organization")
pdf.body_text(
    "Section 2 reviews related work. Section 3 describes the dataset and preprocessing. Section 4 details the "
    "system architecture and methodology. Section 5 covers the experimental setup. Section 6 will present results "
    "and analysis. Section 7 concludes with findings and future directions."
)

# ===== 2. LITERATURE REVIEW =====
pdf.add_page()
pdf.section_title("2", "Literature Review")

pdf.sub_title("2.1", "Content-Based Image Retrieval")
pdf.draft_note("[Partially drafted]")
pdf.body_text(
    "Traditional CBIR systems relied on hand-crafted visual descriptors like SIFT, SURF, and color histograms "
    "(Smeulders et al., 2000; Datta et al., 2008). These approaches work reasonably well for near-duplicate "
    "detection but struggle with semantic queries. Asking \"a cozy living room\" and expecting a color histogram "
    "to understand that is asking too much."
)
pdf.body_text(
    "The shift to deep learning brought feature extractors like ResNet and VGG, which improved representation "
    "quality, but these models were trained for classification, not retrieval. The features they learned were "
    "often too task-specific."
)

pdf.sub_title("2.2", "Vision-Language Models")
pdf.draft_note("[In progress]")
pdf.body_text(
    "CLIP (Radford et al., 2021) changed the retrieval landscape by training a vision encoder and text encoder "
    "jointly on 400 million image-text pairs from the internet. The result is a shared embedding space where "
    "images and text can be directly compared via cosine similarity. For zero-shot retrieval, this is remarkably effective."
)
pdf.body_text(
    "BLIP-2 (Li et al., 2023) and SigLIP (Zhai et al., 2023) built on this foundation with improved training "
    "objectives and architectures. However, most evaluations of these models focus on curated benchmarks like "
    "COCO and Flickr30k, which bear little resemblance to a personal photo library."
)
pdf.body_text(
    "One persistent limitation: CLIP encodes an entire image into a single vector. Spatial information, such as "
    "where objects are located in the frame, gets compressed away. This is likely a problem for queries targeting "
    "specific objects within a larger scene."
)

pdf.sub_title("2.3", "Hybrid Retrieval and Data-Centric Approaches")
pdf.draft_note("[To be expanded]")
pdf.body_text(
    "BM25 (Robertson & Zaragoza, 2009) remains a strong baseline for text retrieval. Recent work has explored "
    "combining traditional keyword matching with neural embeddings for hybrid search. The intuition is straightforward: "
    "embeddings capture semantic meaning, BM25 captures exact keyword matches, and together they cover more ground."
)
pdf.body_text(
    "Query expansion (Kuzi et al., 2016) automatically adds related terms to a search query, improving recall. "
    "For image search, this means mapping \"dog\" to also search for \"puppy,\" \"canine,\" \"pet.\""
)

pdf.sub_title("2.4", "Face Detection and Clustering")
pdf.draft_note("[To be expanded]")
pdf.body_text(
    "Face-based search is a distinct sub-problem. DeepFace (Serengil & Ozpinar, 2020) provides a lightweight "
    "face detection and embedding pipeline. DBSCAN (Ester et al., 1996) is a natural fit for clustering faces "
    "because it does not require specifying the number of clusters in advance, which is not known ahead of "
    "time in a personal collection."
)

pdf.sub_title("2.5", "Gaps in Current Work")
pdf.body_text("From the literature reviewed so far, a few gaps stand out:")
pdf.numbered_item(1, "No published work (that we have found) combines CLIP local crop re-ranking with BM25/VLM hybrid scoring in one system.")
pdf.numbered_item(2, "Personal image retrieval under no-label, mixed-quality conditions is underexplored. Most evaluations assume clean, curated datasets.")
pdf.numbered_item(3, "Face clustering is usually treated as a standalone problem rather than integrated into a retrieval pipeline.")
pdf.ln(2)
pdf.body_text("This project attempts to address all three.")

# ===== 3. DATASET AND PREPROCESSING =====
pdf.add_page()
pdf.section_title("3", "Dataset and Preprocessing")

pdf.sub_title("3.1", "Data Source")
pdf.draft_note("[To be finalized]")
pdf.body_text(
    "The primary evaluation dataset consists of personal images uploaded by test users (with consent). The "
    "collection includes a mix of categories: people, landscapes, food, documents, screenshots, and miscellaneous. "
    "Image quality ranges from high-resolution DSLR photos to low-quality phone camera shots."
)
pdf.body_text(
    "For reproducibility, we plan to supplement with a publicly available subset (e.g., a slice of Open Images)."
)

pdf.sub_title("3.2", "Preprocessing Pipeline")
pdf.bullet("Images resized and normalized for CLIP input (224x224 pixels).")
pdf.bullet("5 crops generated per image: 1 center crop + 4 grid crops for local re-ranking.")
pdf.bullet("VLM descriptions generated via SmolVLM (HuggingFace) as a background process during upload.")
pdf.bullet("Face detection via DeepFace, followed by embedding extraction and DBSCAN clustering.")
pdf.bullet("Query expansion using 100+ semantic mappings.")

pdf.sub_title("3.3", "Data Splits")
pdf.draft_note("[To be finalized]")
pdf.body_text(
    "Planned approach: 80/20 train/test split. If multi-user data is available, user-based splitting ensures "
    "no single user's images appear in both sets."
)

# ===== 4. SYSTEM ARCHITECTURE =====
pdf.section_title("4", "System Architecture and Methodology")

pdf.sub_title("4.1", "System Overview")
pdf.body_text(
    "The system follows a client-server architecture with a React frontend and FastAPI backend. Vector embeddings "
    "are stored in Qdrant, metadata in PostgreSQL, and frequently accessed embeddings are cached in Redis."
)

pdf.sub_title("4.2", "Normal Search (Two-Stage)")
pdf.body_text(
    "Stage 1 (Global Recall): The user query goes through spell checking and query expansion, then is encoded "
    "by the CLIP text encoder. This text embedding is compared against all image global embeddings in Qdrant "
    "to retrieve the Top-K candidates."
)
pdf.body_text(
    "Stage 2 (Local Crop Re-ranking): For each candidate, 5 crops are evaluated (1 center + 4 grid). CLIP "
    "encodes each crop, and the maximum similarity across crops is taken as the local score."
)
pdf.body_text("The final score is computed as:")
pdf.code_block("final_score = 0.6 * global_similarity + 0.4 * max(local_crop_similarities)\ncalibrated_score = sigmoid(final_score * temperature)")
pdf.body_text(
    "The intuition: the global score handles broad relevance, while the local score catches details that the "
    "global embedding may have missed."
)

pdf.sub_title("4.3", "Deep Search (Hybrid BM25 + CLIP)")
pdf.body_text("For deeper searches, we use VLM-generated text descriptions of each image:")
pdf.code_block("hybrid_score = 0.7 * BM25_score(query, description) + 0.3 * CLIP_similarity(query, image)")
pdf.body_text(
    "BM25 handles exact keyword matches against the description text. CLIP handles semantic similarity. "
    "The 70/30 split was initially chosen based on early experiments but will be validated through ablation."
)

pdf.sub_title("4.4", "Face Detection and Clustering")
pdf.body_text(
    "Faces detected by DeepFace are embedded and clustered using DBSCAN (eps=0.5, min_samples=3). Users can "
    "label clusters with names, enabling search-by-person queries."
)

pdf.sub_title("4.5", "Score Calibration")
pdf.body_text(
    "Raw similarity scores are passed through a temperature-scaled sigmoid function. Higher temperatures (25 to 35) "
    "produce stricter, higher-quality results. Lower temperatures (15 to 18) are more lenient, returning more "
    "results at the cost of some noise."
)

# ===== 5. EXPERIMENTAL SETUP =====
pdf.add_page()
pdf.section_title("5", "Experimental Setup")

pdf.sub_title("5.1", "Baselines")
pdf.add_table(
    ["ID", "Model", "Description"],
    [
        ["B0", "CLIP Global Only", "Single global embedding, no re-ranking"],
        ["B1", "BM25 Only", "BM25 on VLM descriptions, no CLIP"],
        ["B2", "CLIP Only Deep", "CLIP similarity only, no BM25"],
    ],
    col_widths=[15, 45, 100]
)

pdf.sub_title("5.2", "Proposed Models")
pdf.add_table(
    ["ID", "Model", "Description"],
    [
        ["M1", "Two-Stage (Global + Local)", "Global recall + 5-crop local re-ranking"],
        ["M2", "Hybrid Deep (BM25 + CLIP)", "0.7 BM25 + 0.3 CLIP on VLM descriptions"],
        ["M3", "Full Pipeline", "M1 + M2 + Face clustering + Query expansion"],
    ],
    col_widths=[15, 55, 90]
)

pdf.sub_title("5.3", "Evaluation Metrics")
pdf.bold_bullet("mAP", "Mean Average Precision, overall retrieval quality")
pdf.bold_bullet("Precision@K", "(K=5, 10), top-K relevance")
pdf.bold_bullet("nDCG@10", "Ranked relevance quality")
pdf.bold_bullet("Query latency", "Response time in milliseconds")
pdf.bold_bullet("ECE", "Expected Calibration Error for confidence scores")
pdf.bold_bullet("Face cluster purity", "Clustering accuracy for RQ4")

pdf.sub_title("5.4", "Planned Experiments")
pdf.draft_note("[Results pending]")
pdf.add_table(
    ["Exp", "Tests", "Metric"],
    [
        ["E1", "B0 vs M1 (local re-ranking effect)", "mAP, P@10"],
        ["E2", "B1, B2 vs M2 (hybrid vs single-mode)", "mAP, P@10"],
        ["E3", "Weight ratio sweep (global/local)", "mAP vs latency"],
        ["E4", "Face clustering quality", "Purity, P@K"],
        ["E5", "Query expansion ablation", "mAP"],
        ["E6", "Crop count ablation (1, 3, 5, 9)", "mAP, latency"],
        ["E7", "Temperature sweep (15 to 35)", "ECE, P@10"],
    ],
    col_widths=[15, 90, 55]
)

pdf.sub_title("5.5", "Implementation Details")
pdf.bullet("Python 3.10+, FastAPI, PyTorch, open-clip-torch")
pdf.bullet("Qdrant (Docker) for vector search")
pdf.bullet("PostgreSQL + SQLAlchemy (async) for metadata")
pdf.bullet("Redis for embedding cache")
pdf.bullet("React 18, Vite for frontend")
pdf.bullet("Tested on consumer GPU (GTX 1660 class) and CPU fallback")
pdf.bullet("Fixed seeds: [42, 123, 456] for reproducibility")

# ===== 6. RESULTS =====
pdf.section_title("6", "Results and Analysis")
pdf.draft_note("[To be completed after experiments are run.]")
pdf.body_text("This section will present:")
pdf.bullet("Head-to-head comparison table (B0, B1, B2 vs M1, M2, M3)")
pdf.bullet("Ablation results for each pipeline component")
pdf.bullet("Error analysis with failure case categories")
pdf.bullet("Calibration analysis at different temperature settings")
pdf.bullet("Robustness tests (typos, low-quality images, unseen categories)")

# ===== 7. CONCLUSION =====
pdf.section_title("7", "Conclusion and Future Work")
pdf.draft_note("[To be written after results.]")
pdf.body_text(
    "Preliminary observations suggest that the two-stage approach and hybrid scoring may offer meaningful "
    "improvements over simpler baselines, but the exact magnitude and conditions remain to be quantified. "
    "Future work could explore fine-tuning CLIP on personal data, multi-modal search (image + text queries), "
    "video frame search, and multi-language query support."
)

# ===== REFERENCES =====
pdf.add_page()
pdf.section_title("", "References")
pdf.draft_note("[Partial list, to be expanded]")
refs = [
    'Radford, A., Kim, J.W., Hallacy, C., et al. (2021). "Learning Transferable Visual Models From Natural Language Supervision." ICML.',
    'Li, J., Li, D., Savarese, S., Hoi, S. (2023). "BLIP-2: Bootstrapping Language-Image Pre-training." ICML.',
    'Robertson, S., Zaragoza, H. (2009). "The Probabilistic Relevance Framework: BM25 and Beyond." Foundations and Trends in IR, 3(4), 333-389.',
    'Ester, M., Kriegel, H.P., Sander, J., Xu, X. (1996). "A Density-Based Algorithm for Discovering Clusters." KDD, 226-231.',
    'Smeulders, A., Worring, M., Santini, S., et al. (2000). "Content-Based Image Retrieval at the End of the Early Years." IEEE TPAMI.',
    'Serengil, S.I., Ozpinar, A. (2020). "DeepFace: A Lightweight Face Recognition Framework." GitHub.',
    'Zhai, X., et al. (2023). "Sigmoid Loss for Language Image Pre-Training." ICCV.',
    'Kuzi, S., Styskin, A., Zuccon, G. (2016). "Query Expansion for Information Retrieval." SIGIR.',
]
for i, ref in enumerate(refs, 1):
    old_margin = pdf.l_margin
    ref_x = old_margin + 5
    text_x = ref_x + 10
    pdf.set_font("Times", "", 10.5)
    pdf.set_x(ref_x)
    pdf.cell(10, 5.5, f"[{i}]")
    pdf.set_left_margin(text_x)
    pdf.set_x(text_x)
    pdf.multi_cell(pdf.w - text_x - pdf.r_margin, 5.5, ref)
    pdf.set_left_margin(old_margin)
    pdf.ln(1.5)

# ===== APPENDICES =====
pdf.ln(6)
pdf.section_title("", "Appendices")
pdf.draft_note("[To be added]")
pdf.bullet("A: Full hyperparameter configurations")
pdf.bullet("B: Extended result tables")
pdf.bullet("C: Sample VLM descriptions and query expansion mappings")
pdf.bullet("D: System deployment guide")

# Save
output_path = r"d:\Media-Search\Research_Paper_Draft.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
