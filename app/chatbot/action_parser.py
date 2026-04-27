from __future__ import annotations

from dataclasses import dataclass
import re

from app.chatbot.prompt_builder import ALLOWED_CHATBOT_ACTIONS
from app.models import CleaningAction, CleaningPlan, DataProfile


ACTION_KEYWORDS = {
    "standardize_column_names": ["standard", "nama kolom", "column", "rapikan nama", "rapikan kolom"],
    "trim_whitespace": ["trim", "whitespace", "spasi"],
    "remove_duplicate_rows": ["duplicate", "duplikat", "hapus duplicate"],
    "parse_date_columns": ["date", "tanggal"],
    "convert_numeric_columns": ["numeric", "angka", "number", "currency"],
    "fill_missing_values": ["missing", "kosong", "null"],
    "create_summary_sheet": ["summary", "ringkasan"],
    "flag_invalid_rows": ["flag", "issue", "masalah", "invalid", "cukup flag", "hanya flag"],
    "sort_rows": ["urutkan", "sort", "sorting"],
    "enrich_with_api": ["enrich", "enrichment", "country", "negara"],
    "create_management_view": ["management", "insight", "manajemen"],
    "create_inefficiency_report": ["inefficiency", "inefisien", "inefficiencies"],
    "normalize_text_casing": ["casing", "lowercase", "uppercase"],
}

NEGATED_ACTION_HINTS = {
    "fill_missing_values": ["jangan isi missing", "jangan isi missing value", "jangan isi null", "tidak usah isi", "cukup flag"],
    "remove_duplicate_rows": ["jangan hapus duplicate", "jangan hapus duplikat"],
}

AMBIGUOUS_ONLY_WORDS = ["bersihkan", "clean", "fix", "perbaiki", "rapikan", "proses"]


@dataclass(frozen=True)
class ParsedInstruction:
    plan: CleaningPlan | None
    needs_clarification: bool = False
    clarification_question: str = ""
    selected_actions: list[str] | None = None


def priority_recommendations(profile: DataProfile) -> dict[str, list[CleaningAction]]:
    recommended = {action.action_name: action for action in recommended_actions(profile)}
    highly_recommended_names = ["standardize_column_names", "trim_whitespace", "parse_date_columns", "convert_numeric_columns", "flag_invalid_rows", "create_inefficiency_report"]
    optional_names = ["create_summary_sheet", "normalize_text_casing", "enrich_with_api", "create_management_view"]
    risky_names = ["remove_duplicate_rows", "fill_missing_values"]
    return {
        "Highly recommended": [recommended[name] for name in highly_recommended_names if name in recommended],
        "Optional": [recommended[name] for name in optional_names if name in recommended],
        "Risky / requires confirmation": [recommended[name] for name in risky_names if name in recommended],
    }


def recommended_actions(profile: DataProfile) -> list[CleaningAction]:
    actions = [
        CleaningAction(action_name="standardize_column_names", reason="Nama kolom lebih konsisten untuk proses berikutnya."),
        CleaningAction(action_name="trim_whitespace", reason="Menghapus spasi liar pada nilai teks."),
    ]
    if profile.duplicate_count > 0:
        actions.append(CleaningAction(action_name="remove_duplicate_rows", reason="Duplicate rows terdeteksi pada data."))
    if profile.suspected_date_columns:
        actions.append(CleaningAction(action_name="parse_date_columns", columns=profile.suspected_date_columns, reason="Kolom ini terlihat seperti tanggal."))
    numeric_text = [
        col for col in profile.suspected_numeric_columns
        if profile.dtypes.get(col, "").lower() in {"object", "str", "string"}
    ]
    if numeric_text:
        actions.append(CleaningAction(action_name="convert_numeric_columns", columns=numeric_text, reason="Kolom ini terlihat numeric tapi masih berupa teks."))
    if sum(profile.missing_values.values()) > 0:
        actions.append(CleaningAction(action_name="fill_missing_values", reason="Missing values ditemukan dan bisa diisi dengan default konservatif."))
    if profile.casing_inconsistencies:
        actions.append(CleaningAction(action_name="normalize_text_casing", columns=list(profile.casing_inconsistencies), parameters={"case": "lower"}, reason="Terdapat variasi casing pada nilai teks."))
    actions.extend(
        [
            CleaningAction(action_name="enrich_with_api", reason="Menambahkan enrichment API/fallback jika kolom negara tersedia."),
            CleaningAction(action_name="create_summary_sheet", reason="Membuat sheet ringkasan untuk review cepat."),
            CleaningAction(action_name="create_management_view", reason="Membuat management insight yang actionable."),
            CleaningAction(action_name="create_inefficiency_report", reason="Membuat report inefficiency agar masalah operasional terlihat jelas."),
            CleaningAction(action_name="flag_invalid_rows", reason="Membuat sheet issue agar perubahan tetap audit-able."),
        ]
    )
    return actions


def plan_from_selected_actions(
    selected_action_names: list[str],
    profile: DataProfile,
    user_instruction: str | None = None,
) -> CleaningPlan:
    recommended = {action.action_name: action for action in recommended_actions(profile)}
    actions: list[CleaningAction] = []
    for name in selected_action_names:
        if name not in ALLOWED_CHATBOT_ACTIONS:
            continue
        if name in recommended:
            actions.append(recommended[name])
        elif name == "parse_date_columns":
            actions.append(CleaningAction(action_name=name, columns=profile.suspected_date_columns, reason="User selected date parsing."))
        elif name == "convert_numeric_columns":
            actions.append(CleaningAction(action_name=name, columns=profile.suspected_numeric_columns, reason="User selected numeric conversion."))
        elif name == "sort_rows":
            actions.append(CleaningAction(action_name=name, reason="User selected row sorting."))
        else:
            actions.append(CleaningAction(action_name=name, reason="User selected this safe action."))
    return CleaningPlan(actions=actions, user_instruction=user_instruction)


def sanitize_cleaning_plan(plan: CleaningPlan) -> CleaningPlan:
    actions = [
        action
        for action in plan.actions
        if action.enabled and action.action_name in ALLOWED_CHATBOT_ACTIONS
    ]
    return CleaningPlan(actions=actions, user_instruction=plan.user_instruction)


def _negated_actions(text: str) -> set[str]:
    return {
        action
        for action, hints in NEGATED_ACTION_HINTS.items()
        if any(hint in text for hint in hints)
    }


def parse_user_text_to_plan(text: str, profile: DataProfile) -> CleaningPlan:
    parsed = parse_user_instruction(text, profile)
    if parsed.needs_clarification or parsed.plan is None:
        return CleaningPlan(actions=[], user_instruction=text)
    return parsed.plan


def parse_user_instruction(text: str, profile: DataProfile) -> ParsedInstruction:
    lowered = text.lower().strip()
    sort_request = _parse_sort_request(lowered, profile)
    if sort_request == "ambiguous":
        return ParsedInstruction(
            plan=None,
            needs_clarification=True,
            clarification_question=(
                "Saya menangkap Anda ingin mengurutkan data, tapi kolomnya belum jelas. "
                f"Sebutkan salah satu kolom ini: {', '.join(profile.column_names)}."
            ),
            selected_actions=[],
        )
    negated = _negated_actions(lowered)
    selected = [
        action
        for action, keywords in ACTION_KEYWORDS.items()
        if action not in negated and any(keyword in lowered for keyword in keywords)
    ]
    only_ambiguous = any(word in lowered for word in AMBIGUOUS_ONLY_WORDS) and not selected
    if only_ambiguous or not lowered:
        return ParsedInstruction(
            plan=None,
            needs_clarification=True,
            clarification_question=(
                "Instruksinya masih terlalu umum. Anda ingin saya melakukan apa secara spesifik: "
                "hapus duplicate, parse tanggal, convert numeric, hanya flag issue, atau jalankan rekomendasi?"
            ),
            selected_actions=[],
        )
    if any(word in lowered for word in ["semua", "all", "recommended", "rekomendasi"]):
        selected = [action.action_name for action in recommended_actions(profile)]
    if not selected:
        return ParsedInstruction(
            plan=None,
            needs_clarification=True,
            clarification_question=(
                "Saya belum bisa memetakan instruksi itu ke action yang aman. Coba sebutkan tindakan seperti "
                "`hapus duplicate`, `parse tanggal`, `convert numeric`, `buat summary`, atau `flag missing values`."
            ),
            selected_actions=[],
        )
    if "cukup flag" in lowered or "hanya flag" in lowered:
        selected = [action for action in selected if action not in {"fill_missing_values", "remove_duplicate_rows"}]
        if "flag_invalid_rows" not in selected:
            selected.append("flag_invalid_rows")
    plan = plan_from_selected_actions(selected, profile, user_instruction=text)
    if sort_request:
        plan.actions = [
            action for action in plan.actions if action.action_name != "sort_rows"
        ]
        plan.actions.append(sort_request)
    return ParsedInstruction(plan=plan, selected_actions=[action.action_name for action in plan.actions])


def _normalize_column_text(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", value.lower())


def _parse_sort_request(text: str, profile: DataProfile) -> CleaningAction | str | None:
    if not any(word in text for word in ["urutkan", "sort", "sorting"]):
        return None
    descending = any(word in text for word in ["desc", "descending", "menurun", "terbesar", "tertinggi", "besar ke kecil"])
    ascending = not descending
    normalized_text = _normalize_column_text(text)
    aliases = {
        "gaji": ["gaji", "salary", "upah", "payroll", "wage"],
        "departemen": ["departemen", "department", "divisi", "division"],
        "tanggal": ["tanggal", "date"],
        "nama": ["nama", "name"],
    }
    for col in profile.column_names:
        normalized_col = _normalize_column_text(col)
        if normalized_col and normalized_col in normalized_text:
            return CleaningAction(
                action_name="sort_rows",
                columns=[col],
                parameters={"ascending": ascending},
                reason=f"User asked to sort rows by {col}.",
            )
    for canonical, values in aliases.items():
        if any(alias in normalized_text for alias in values):
            for col in profile.column_names:
                normalized_col = _normalize_column_text(col)
                if normalized_col in values or canonical in normalized_col or any(alias in normalized_col for alias in values):
                    return CleaningAction(
                        action_name="sort_rows",
                        columns=[col],
                        parameters={"ascending": ascending},
                        reason=f"User asked to sort rows by {col}.",
                    )
    return "ambiguous"
