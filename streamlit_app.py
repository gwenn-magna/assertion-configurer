import streamlit as st
import json
import uuid
import ast

# Core fields shared across check types
core_fields = {
    "name": {"type": "string", "required": True},
    "id": {"type": "string", "optional": True, "default": lambda: f"assertion_{uuid.uuid4().hex[:8]}"},
    "failtype": {"type": "select", "options": ["fail", "warn"], "default": "fail"},
    "check_type": {"type": "fixed", "value_from_parent": True}
}

# Processor options for postproc
known_processors = [
    "fasta-summary", "bam-index-stats", "vcf-header", "flagstat",
    "bcftools_stats", "miqa_steps_log", "bam_reads_by_name",
    "bam_region_sample", "miqa_ls_txt"
]

# Type-specific schema extensions
schemas = {
    "postproc_results": {
        "fields": {
            "processor_key": {"type": "select", "options": known_processors, "required": True},
            "stat": {"type": "expression", "placeholder": "e.g. data.format == 'fasta' and data.valid_format"},
            "postprocessed_file_pattern": {"type": "string", "placeholder": "e.g. .*fasta"},
            "item_typ1e": {"type": "fixed", "value": "outputfile"},
        }
    },
    "tabular_mdo_eval": {
        "fields": {
            "stat": {"type": "expression", "placeholder": "e.g. data.rows.map('%PF').mean() > 0.9"},
            "file_rules": {"type": "string", "placeholder": "e.g. .*\\.csv$"},
            "delimiter": {"type": "string", "placeholder": ","},
            "comment_character": {"type": "string", "optional": True, "placeholder": "#"},
        }
    }
}

# ---- Streamlit UI ----
st.set_page_config(page_title="Miqa Assertion Builder", layout="wide")
st.title("🧪 Miqa Assertion Builder")

# Step 1: Select check type
check_type = st.selectbox("Select Assertion Type", list(schemas.keys()))
fields = {**core_fields, **schemas[check_type]["fields"]}

# Step 2: Build form
output = {}
st.markdown("#### ✍️ Configure Your Test")

for key, meta in fields.items():
    ftype = meta["type"]
    default = meta.get("default", "")
    placeholder = meta.get("placeholder", "")
    value = None

    if callable(default):
        default = default()

    if ftype == "fixed":
        output[key] = check_type if meta.get("value_from_parent") else meta["value"]
        continue

    if ftype == "string":
        value = st.text_input(key, value=default, placeholder=placeholder)
    elif ftype == "expression":
        value = st.text_area(key, value=default, placeholder=placeholder)
        if value.strip():
            try:
                ast.parse(value, mode="eval")
                st.success("✅ Syntactically valid expression (this may still not be a valid expression for your specific dataset; try the assertion to confirm).")
            except SyntaxError as e:
                st.error(f"❌ Invalid expression: {e.msg}")
    elif ftype == "select":
        value = st.selectbox(key, options=meta["options"], index=meta["options"].index(default) if default in meta["options"] else 0)

    if value or (meta.get("optional") and value == ""):
        output[key] = value

# Step 3: Show and download output
st.markdown("#### 🧾 Generated JSON")
st.code(json.dumps(output, indent=2), language="json")

from streamlit.components.v1 import html

import uuid
test_json = json.dumps(output, indent=2)
unique_id = str(uuid.uuid4()).replace("-", "")
text_id = f"text_{unique_id}"
toast_id = f"toast_{unique_id}"

html(f"""
<div style="margin-top: 1rem;">
    <button onclick="applyTest_{unique_id}()" style="
        padding: 8px 16px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 1rem;
        cursor: pointer;
    ">✅ Apply This Assertion</button>

    <textarea id="{text_id}" style="position: absolute; left: -9999px;">{test_json}</textarea>

    <div id="{toast_id}" style="
        display: none;
        position: fixed;
        top: 30px;
        left: 50%;
        transform: translateX(-50%);
        background-color: #28a745;
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        z-index: 9999;
    ">
        ✅ Assertion sent! Use Cmd/Ctrl + Shift + V to paste it in your app.
    </div>

    <script>
    function applyTest_{unique_id}() {{
        try {{
            var text = document.getElementById("{text_id}").value;
            var json = JSON.parse(text);
            window.top.postMessage({{
                type: "miqa-test-apply-direct",
                payload: json
            }}, "*");

            var toast = document.getElementById("{toast_id}");
            toast.style.display = "block";
            setTimeout(function() {{
                toast.style.display = "none";
            }}, 3000);
        }} catch (err) {{
            console.error("Failed to send test:", err);
        }}
    }}
    </script>
</div>
""")
