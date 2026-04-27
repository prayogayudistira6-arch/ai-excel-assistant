from __future__ import annotations

from app.models import DataProfile


ALLOWED_CHATBOT_ACTIONS = [
    "standardize_column_names",
    "trim_whitespace",
    "remove_duplicate_rows",
    "parse_date_columns",
    "convert_numeric_columns",
    "fill_missing_values",
    "normalize_text_casing",
    "flag_invalid_rows",
    "sort_rows",
    "enrich_with_api",
    "create_summary_sheet",
    "create_management_view",
    "create_inefficiency_report",
    "style_excel_output",
]

def build_review_prompt(profile: DataProfile) -> str:
    return (
        "Review this spreadsheet profile and recommend safe cleaning actions. "
        "Do not write code. Only use allowed actions. "
        f"Allowed actions: {', '.join(ALLOWED_CHATBOT_ACTIONS)}\n"
        f"Profile JSON: {profile.model_dump_json()}"
    )


def build_greeting() -> str:
    return (
        "Halo, saya siap membantu membersihkan spreadsheet Anda. "
        "Upload file CSV atau XLSX, lalu saya akan membaca struktur datanya, menjelaskan masalah yang ditemukan, "
        "dan menunggu pilihan Anda sebelum menjalankan cleaning."
    )


def build_natural_review(profile: DataProfile) -> str:
    total_missing = sum(profile.missing_values.values())
    numeric_text = [
        col for col in profile.suspected_numeric_columns
        if profile.dtypes.get(col, "").lower() in {"object", "str", "string"}
    ]
    lines = [
        f"Saya sudah membaca `{profile.file_name}`. Secara sederhana, datanya berisi {profile.rows} baris dan {profile.columns} kolom.",
        "",
        "File ini memiliki beberapa potensi inefficiency: missing values, duplicate rows, format tanggal tidak konsisten, dan kolom numeric yang masih bertipe text.",
        "",
        "Saya menemukan beberapa hal:",
        f"- {total_missing} missing values",
        f"- {profile.duplicate_count} duplicate rows",
        f"- {len(profile.suspected_date_columns)} kolom kemungkinan berisi tanggal",
        f"- {len(numeric_text)} kolom numeric masih bertipe text",
        f"- {len(profile.casing_inconsistencies)} kolom memiliki potensi inkonsistensi casing/string",
    ]
    if profile.invalid_date_counts:
        lines.append(f"- {sum(profile.invalid_date_counts.values())} nilai tanggal terlihat invalid")
    nonstandard = [col for col in profile.column_names if col.strip().lower().replace(" ", "_") != col]
    if nonstandard:
        lines.append("- beberapa nama kolom belum standar")
    lines.extend(
        [
            "",
            "Saya bisa melakukan beberapa tindakan:",
            "1. Standardisasi nama kolom",
            "2. Trim whitespace",
            "3. Hapus duplicate rows",
            "4. Parse kolom tanggal",
            "5. Convert kolom numeric",
            "6. Isi missing values",
            "7. Buat summary sheet",
            "8. Buat flagged issues sheet",
            "",
            "Prioritas saya: standardisasi nama kolom, trim whitespace, parse tanggal, convert numeric, dan flagged issues biasanya aman. "
            "Menghapus duplicate dan mengisi missing values perlu konfirmasi karena bisa mengubah isi data.",
            "",
            "Management-level inefficiencies detected:",
            "- Duplicate records may distort reporting accuracy",
            "- Missing owner/assignee may cause accountability gaps",
            "- Invalid dates may delay timeline tracking",
            "- Inconsistent status values may make dashboards unreliable",
            "- Numeric fields stored as text may break financial calculations",
            "",
            "Silakan pilih tindakan yang ingin dijalankan.",
        ]
    )
    return "\n".join(lines)
