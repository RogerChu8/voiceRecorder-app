import streamlit as st
import datetime
import wave
from audio_recorder_streamlit import audio_recorder
import io
import zipfile
import os
import pandas as pd

# Custom CSS for layout and colors
st.markdown("""
    <style>
    .record-button button {
        background-color: #00FF00 !important;
        color: black !important;
    }
    .record-button button:hover {
        background-color: #FF0000 !important;
        color: black !important;
    }
    .play-button button {
        background-color: #FFFFFF !important;
        color: black !important;
    }
    .play-button button:hover {
        background-color: #DDDDDD !important;
        color: black !important;
    }
    .treeview {
        overflow-y: scroll;
        height: 300px;
        border: 1px solid #ccc;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
    }
    .stApp h1 {
        font-size: 180%;
    }
    </style>
""", unsafe_allow_html=True)

# App title
st.title("Voice Script Recorder")

# Accept and remove functions
def accept(s):
    if st.session_state.temp_audio:
        s['status'] = 'Completed'
        s['record_time'] = st.session_state.record_time
        today = datetime.date.today().strftime('%Y%m%d')
        num = f"{s['num']:04d}"
        base_name = f"script{num}_{today}"
        # Delete all existing files for this num
        keys_to_delete = [k for k in st.session_state.files if k.startswith(f"script{num}_")]
        for k in keys_to_delete:
            del st.session_state.files[k]
        # Save new files
        txt_bytes = s['text'].encode()
        st.session_state.files[base_name + '.txt'] = txt_bytes
        st.session_state.files[base_name + '.wav'] = st.session_state.temp_audio
        st.download_button("Download .txt", txt_bytes, file_name=base_name + '.txt', key="txt_down")
        st.download_button("Download .wav", st.session_state.temp_audio, file_name=base_name + '.wav', key="wav_down")
        if s['num'] in st.session_state.removed_nums:
            st.session_state.removed_nums.remove(s['num'])
        s['latest_date'] = today
        st.session_state.temp_audio = None
        if st.session_state.current_index + 1 < len(st.session_state.scripts):
            st.session_state.current_index += 1
        st.rerun()

def remove(s):
    s['status'] = 'Removed'
    s['record_time'] = 0.0
    if s['num'] not in st.session_state.removed_nums:
        st.session_state.removed_nums.append(s['num'])
    st.session_state.temp_audio = None
    # Delete associated files
    num_str = f"{s['num']:04d}"
    keys_to_delete = [k for k in st.session_state.files if k.startswith(f"script{num_str}_")]
    for k in keys_to_delete:
        del st.session_state.files[k]
    if 'latest_date' in s:
        del s['latest_date']
    st.rerun()

# Function to update statuses based on uploaded files and removed
def update_statuses_and_texts(uploaded_files):
    paired = {}
    for file in uploaded_files or []:
        try:
            if file.name.endswith('.txt') or file.name.endswith('.wav'):
                parts = file.name.split('_')
                if len(parts) == 2 and parts[0].startswith('script') and len(parts[0]) == 10:
                    num_str = parts[0][6:]
                    date_part = parts[1].split('.')[0]
                    if num_str.isdigit() and date_part.isdigit() and len(date_part) == 8:
                        num = int(num_str)
                        if num not in paired:
                            paired[num] = []
                        bytes_data = file.read()
                        st.session_state.files[file.name] = bytes_data
                        if file.name.endswith('.txt'):
                            text = bytes_data.decode().strip()
                            paired[num].append((date_part, 'txt', text))
                        elif file.name.endswith('.wav'):
                            with wave.open(io.BytesIO(bytes_data), 'rb') as w:
                                frames = w.getnframes()
                                rate = w.getframerate()
                                duration = frames / float(rate) if rate else 0.0
                            paired[num].append((date_part, 'wav', duration))
        except Exception as e:
            st.warning(f"Error processing file {file.name}: {str(e)}")

    for s in st.session_state.scripts:
        num = s['num']
        if num in st.session_state.removed_nums:
            s['status'] = 'Removed'
            s['record_time'] = 0.0
        elif num in paired:
            dates = {}
            for entry in paired[num]:
                date, typ, val = entry
                if date not in dates:
                    dates[date] = {}
                dates[date][typ] = val
            complete_dates = [date for date in dates if 'txt' in dates[date] and 'wav' in dates[date]]
            if complete_dates:
                complete_dates.sort(reverse=True)  # latest first
                latest_date = complete_dates[0]
                s['text'] = dates[latest_date]['txt']
                s['record_time'] = dates[latest_date]['wav']
                s['status'] = 'Completed'
                s['latest_date'] = latest_date
            else:
                s['status'] = 'Not started'
                s['record_time'] = 0.0
                if 'latest_date' in s:
                    del s['latest_date']
        else:
            s['status'] = 'Not started'
            s['record_time'] = 0.0
            if 'latest_date' in s:
                del s['latest_date']

    # Cleanup: keep only latest files for completed scripts
    for s in st.session_state.scripts:
        num_str = f"{s['num']:04d}"
        if s['status'] == 'Completed' and 'latest_date' in s:
            keep_txt = f"script{num_str}_{s['latest_date']}.txt"
            keep_wav = f"script{num_str}_{s['latest_date']}.wav"
            keys_to_delete = [k for k in st.session_state.files if k.startswith(f"script{num_str}_") and k not in [keep_txt, keep_wav]]
            for k in keys_to_delete:
                del st.session_state.files[k]
        else:
            keys_to_delete = [k for k in st.session_state.files if k.startswith(f"script{num_str}_")]
            for k in keys_to_delete:
                del st.session_state.files[k]

# Session state
if 'scripts' not in st.session_state:
    st.session_state.scripts = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = -1
if 'temp_audio' not in st.session_state:
    st.session_state.temp_audio = None
if 'removed_nums' not in st.session_state:
    st.session_state.removed_nums = []
if 'record_time' not in st.session_state:
    st.session_state.record_time = 0.0
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = ""
if 'files' not in st.session_state:
    st.session_state.files = {}
if 'last_selected' not in st.session_state:
    st.session_state.last_selected = -1

# Top row: Mic (skip), Load buttons
col_mic, col_load_new, col_continue = st.columns([2,1,1])
with col_mic:
    st.write("Select Microphone: Browser Default")
with col_load_new:
    if st.button("Start New Project"):
        st.session_state.load_mode = "new"
with col_continue:
    if st.button("Continue Project"):
        st.session_state.load_mode = "existing"

# Load logic
if 'load_mode' in st.session_state:
    if st.session_state.load_mode =="new":
        scripts_uploader = st.file_uploader("Select scripts.txt File to Upload", type="txt", key="new_scripts")
        if scripts_uploader:
            lines = scripts_uploader.read().decode().splitlines()
            st.session_state.scripts = []
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    num_str, text = line.split('.', 1)
                    num = int(num_str)
                    text = text.strip()
                    st.session_state.scripts.append({'num': num, 'text': text, 'status': 'Not started', 'record_time': 0.0})
            st.session_state.removed_nums = []
            st.session_state.output_dir = "New Project"
            if st.session_state.scripts:
                st.session_state.current_index = 0
            del st.session_state.load_mode
            st.rerun()
    elif st.session_state.load_mode =="existing":
        st.info("Upload all files from your existing project directory (including scripts.txt, removed.txt or scripts.removed, and all .txt/.wav files). The app will verify scripts.txt is included.")
        existing_files = st.file_uploader("Upload all files from the directory", type=["txt", "wav"], accept_multiple_files=True, key="exist_files")
        has_scripts = any(f.name == "scripts.txt" for f in existing_files)
        if existing_files:
            if not has_scripts:
                st.error("No scripts.txt found in uploaded files. Please include it and retry.")
            else:
                scripts_file = next(f for f in existing_files if f.name == "scripts.txt")
                lines = scripts_file.read().decode().splitlines()
                st.session_state.scripts = []
                for line in lines:
                    line = line.strip()
                    if line and line[0].isdigit() and '.' in line:
                        num_str, text = line.split('.', 1)
                        num = int(num_str)
                        text = text.strip()
                        st.session_state.scripts.append({'num': num, 'text': text, 'status': 'Not started', 'record_time': 0.0})
                removed_file = next((f for f in existing_files if f.name in ["scripts.removed", "removed.txt"]), None)
                if removed_file:
                    removed_lines = removed_file.read().decode().splitlines()
                    st.session_state.removed_nums = [int(line.strip()) for line in removed_lines if line.strip().isdigit()]
                else:
                    st.session_state.removed_nums = []
                other_files = [f for f in existing_files if f.name not in ["scripts.txt", "scripts.removed", "removed.txt"]]
                update_statuses_and_texts(other_files)
                st.session_state.output_dir = "Uploaded Project"
                if st.session_state.scripts:
                    st.session_state.current_index = 0
                del st.session_state.load_mode
                st.rerun()

# Subdir label, Add, Update
col_subdir, col_add, col_update = st.columns([2,1,1])
with col_subdir:
    st.write(f"Output Subdirectory: {st.session_state.output_dir}")
with col_add:
    if st.button("Add Scripts"):
        add_uploader = st.file_uploader("Select Additional Scripts File", type="txt", key="add_scripts")
        if add_uploader:
            lines = add_uploader.read().decode().splitlines()
            new_texts = []
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    _, text = line.split('.', 1)
                    text = text.strip()
                    new_texts.append(text)
            existing_texts = set(s['text'].strip() for s in st.session_state.scripts)
            new_entries = [text for text in new_texts if text.strip() not in existing_texts]
            if new_entries:
                max_num = max(s['num'] for s in st.session_state.scripts) if st.session_state.scripts else 0
                for text in new_entries:
                    max_num += 1
                    st.session_state.scripts.append({'num': max_num, 'text': text, 'status': 'Not started', 'record_time': 0.0})
                st.rerun()
with col_update:
    if st.button("Update Scripts"):
        scripts_content = "\n".join(f"{s['num']}. {s['text']}" for s in st.session_state.scripts)
        st.download_button("Download updated scripts.txt", scripts_content.encode(), file_name="scripts.txt", key="update_download")

# Scripts list
if st.session_state.scripts:
    st.subheader("Scripts")

    def style_rows(row):
        if row['Status'] == 'Completed':
            return ['background-color: lightgreen'] * len(row)
        elif row['Status'] == 'Removed':
            return ['background-color: lightgrey'] * len(row)
        else:
            return [''] * len(row)

    data = [{'Num': s['num'], 'Status': s['status'], 'Preview': s['text'][:50] + ('...' if len(s['text']) > 50 else '')} for s in st.session_state.scripts]
    df = pd.DataFrame(data)
    styled_df = df.style.apply(style_rows, axis=1)
    grid_return = st.dataframe(styled_df, use_container_width=True, hide_index=True, selection_mode='single-row', height=300, on_select="rerun", key="scripts_table")
    selected_rows = grid_return.selection.rows
    if selected_rows:
        st.session_state.current_index = selected_rows[0]
    else:
        st.session_state.current_index = -1

# Edit script
s = st.session_state.scripts[st.session_state.current_index] if st.session_state.current_index >= 0 else None
if s:
    if st.session_state.last_selected != st.session_state.current_index:
        old_index = st.session_state.last_selected
        if old_index >= 0:
            old_key = f"edit_text_{old_index}"
            if old_key in st.session_state:
                old_edited = st.session_state[old_key]
                old_s = st.session_state.scripts[old_index]
                if old_edited != old_s['text']:
                    old_s['text'] = old_edited
        st.session_state.last_selected = st.session_state.current_index
        if s['status'] == 'Completed' and 'latest_date' in s:
            wav_filename = f"script{s['num']:04d}_{s['latest_date']}.wav"
            st.session_state.temp_audio = st.session_state.files.get(wav_filename)
            st.session_state.record_time = s['record_time']
        else:
            st.session_state.temp_audio = None
            st.session_state.record_time = 0.0
else:
    st.session_state.temp_audio = None
    st.session_state.record_time = 0.0
st.write("Edit Script:")
edit_key = f"edit_text_{st.session_state.current_index}" if st.session_state.current_index >= 0 else "edit_text_none"
edited_text = st.text_area("", value=s['text'] if s else "", height=150, key=edit_key, disabled=s is None)
if s and edited_text != s['text']:
    s['text'] = edited_text

# Record time
st.write(f"Record time: {st.session_state.record_time:.1f} seconds")

# Buttons row
col_record, col_play, col_accept, col_remove = st.columns(4)
with col_record:
    st.markdown('<div class="record-button">', unsafe_allow_html=True)
    audio_bytes = audio_recorder(text="", recording_color="#FF0000", neutral_color="#00FF00", key=f"recorder_{st.session_state.current_index}")
    st.markdown('</div>', unsafe_allow_html=True)
    if audio_bytes and s:
        st.session_state.temp_audio = audio_bytes
        with wave.open(io.BytesIO(audio_bytes), 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            st.session_state.record_time = frames / rate if rate else 0.0
with col_play:
    st.markdown('<div class="play-button">', unsafe_allow_html=True)
    if st.button("►", disabled=s is None):
        if st.session_state.temp_audio:
            st.audio(st.session_state.temp_audio, format="audio/wav")
    st.markdown('</div>', unsafe_allow_html=True)
with col_accept:
    if st.button("Accept", disabled=s is None):
        accept(s)
with col_remove:
    if st.button("Remove", disabled=s is None):
        remove(s)

# Download Project button at the bottom
if st.session_state.scripts:
    if st.button("Download Project"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Add scripts.txt
            scripts_content = "\n".join(f"{s['num']}. {s['text']}" for s in st.session_state.scripts)
            zip_file.writestr("scripts.txt", scripts_content.encode())
            # Add removed.txt (renamed from scripts.removed)
            removed_content = "\n".join(str(num) for num in st.session_state.removed_nums)
            zip_file.writestr("removed.txt", removed_content.encode())
            # Add all .txt and .wav from session files
            for filename, data in st.session_state.files.items():
                if filename.endswith('.txt') or filename.endswith('.wav'):
                    zip_file.writestr(filename, data)
        zip_buffer.seek(0)
        today = datetime.date.today().strftime('%Y%m%d')
        st.download_button("Download Project Zip", zip_buffer, file_name=f"project_{today}.zip")