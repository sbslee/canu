import os, time, yaml, pickle, tempfile
from pathlib import Path
import streamlit as st
import streamlit_authenticator as stauth
import openai
from PIL import Image

class Container():
    def __init__(self, role, blocks):
        self.container = st.empty()
        self.role = role
        self.blocks = blocks
        self.code_interpreter_files = {}

    def _write_blocks(self):
        avatar = None
        if self.role == "assistant" and "assistant_avatar" in st.session_state:
            avatar = Image.open(st.session_state.assistant_avatar)
        with st.chat_message(self.role, avatar=avatar):
            for block in self.blocks:
                if block['type'] == 'text':
                    st.write(block['content'], unsafe_allow_html=True)
                elif block['type'] == 'code':
                    st.code(block['content'])
                elif block['type'] == 'image':
                    st.image(block['content'])
            if self.code_interpreter_files:
                for filename, content in self.code_interpreter_files.items():
                    if filename.endswith('.csv'):
                        mime = "text/csv"
                    elif filename.endswith('.png'):
                        mime = "image/png"
                    else:
                        mime = "text/plain"        
                    st.download_button(
                        label=f"{filename}",
                        data=content,
                        file_name=filename,
                        mime=mime,
                        key=f"download_button_{st.session_state.download_button_key}"
                    )
                    st.session_state.download_button_key += 1

    def get_content(self):
        content = []
        for block in self.blocks:
            if block['type'] == 'text':
                content.append({"type": "text", "text": block['content']})
        return content

    def write_blocks(self, stream=False):
        if stream:
            with self.container:
                self._write_blocks()
        else:
            self._write_blocks()

class EventHandler(openai.AssistantEventHandler):
    def __init__(self, container=None):
        super().__init__()
        self.container = container
        self.redundant = container is not None

    def on_text_delta(self, delta, snapshot):
        if self.container is None:
            self.container = Container("assistant", [])
        if not self.container.blocks or self.container.blocks[-1]['type'] != 'text':
            self.container.blocks.append({'type': 'text', 'content': ""})
        if delta.annotations is not None:
            for annotation in delta.annotations:
                if annotation.type == "file_citation":
                    file = st.session_state.client.files.retrieve(annotation.file_citation.file_id)
                    delta.value = delta.value.replace(annotation.text, f"""<a href="#" title="{file.filename}">[❞]</a>""")
                elif annotation.type == "file_path":
                    file = st.session_state.client.files.retrieve(annotation.file_path.file_id)
                    content = st.session_state.client.files.content(file.id)
                    filename = os.path.basename(file.filename)
                    self.container.code_interpreter_files[filename] = content.read()
        if delta.value is not None:
            self.container.blocks[-1]["content"] += delta.value
        self.container.write_blocks(stream=True)

    def on_image_file_done(self, image_file):
        if self.container is None:
            self.container = Container("assistant", [])
        if not self.container.blocks or self.container.blocks[-1]['type'] != 'image':
            self.container.blocks.append({'type': 'image', 'content': ""})
        image_data = st.session_state.client.files.content(image_file.file_id)
        image_data_bytes = image_data.read()
        self.container.blocks[-1]["content"] = image_data_bytes
        self.container.write_blocks(stream=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "function":
            pass
        elif delta.type == "code_interpreter":
            if self.container is None:
                self.container = Container("assistant", [])
            if delta.code_interpreter.input:
                if not self.container.blocks or self.container.blocks[-1]['type'] != 'code':
                    self.container.blocks.append({'type': 'code', 'content': ""})
                self.container.blocks[-1]["content"] += delta.code_interpreter.input
            self.container.write_blocks(stream=True)

    def submit_tool_outputs(self, tool_outputs, run_id):
        with st.session_state.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(self.container),
        ) as stream:
            stream.until_done()

    def on_end(self):
        if self.container is not None and not self.redundant:
            st.session_state.containers.append(self.container)

    def on_event(self, event):
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

def update_yaml_file():
    with open("./auth.yaml", 'w', encoding="utf-8-sig") as f:
        yaml.dump(st.session_state.config, f, allow_unicode=True)

def authenticate():
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "authenticator" not in st.session_state:
        with open("./auth.yaml") as f:
            config = yaml.load(f, Loader=yaml.loader.SafeLoader)
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
        )
        st.session_state.config = config
        st.session_state.authenticator = authenticator

def add_message(role, content):
    create_message(role, content)
    st.session_state.containers.append(
        Container(role, [{'type': 'text', 'content': content}])
    )

def write_stream(event_handler=None):
    if event_handler is None:
        event_handler = EventHandler()
    if not is_thread_locked():
        with st.session_state.client.beta.threads.runs.stream(
            thread_id=st.session_state.thread.id,
            assistant_id=st.session_state.assistant.id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

def show_login_page():
    labels = {
        'Form name': {'English': 'Login', 'Korean': '로그인'},
        'Username': {'English': 'Username', 'Korean': '아이디'},
        'Password': {'English': 'Password', 'Korean': '비밀번호'},
        'Login': {'English': 'Login', 'Korean': '로그인'},
        'Incorrect credential': {'English': 'The ID or password is incorrect.', 'Korean': '아이디 또는 비밀번호가 잘못되었습니다.'},
    }
    language = st.radio("NONE", ["Korean", "English"], label_visibility="hidden", horizontal=True)
    st.session_state.language = language
    st.session_state.name, st.session_state.authentication_status, st.session_state.username = st.session_state.authenticator.login(location="main", fields={'Form name': labels['Form name'][st.session_state.language], 'Username': labels['Username'][st.session_state.language], 'Password': labels['Password'][st.session_state.language], 'Login': labels['Login'][st.session_state.language]})
    if st.session_state.authentication_status:
        st.session_state.page = "chatbot"
        st.rerun()
    elif st.session_state.authentication_status is False:
        st.error(labels['Incorrect credential'][st.session_state.language])
    elif st.session_state.authentication_status is None:
        pass

def show_profile_page():
    labels = {
        'Form name': {'English': 'Reset password', 'Korean': '비밀번호 변경'},
        'Current password': {'English': 'Current password', 'Korean': '현재 비밀번호'},
        'New password': {'English': 'New password', 'Korean': '새로운 비밀번호'},
        'Repeat password': {'English': 'Repeat password', 'Korean': '새로운 비밀번호 확인'},
        'Reset': {'English': 'Reset', 'Korean': '변경'},
        'Go back': {'English': 'Go back', 'Korean': '돌아가기'},
        'Change success': {'English': 'Password has been successfully changed.', 'Korean': '비밀번호가 성공적으로 변경되었습니다.'},
    }
    if "file_uploader_key" in st.session_state:
        uploaded_files = get_uploaded_files()
    if st.sidebar.button(labels['Go back'][st.session_state.language]):
        st.session_state.page = "chatbot"
        st.rerun()
    if st.session_state.authenticator.reset_password(st.session_state.username, fields={'Form name': labels['Form name'][st.session_state.language], 'Current password': labels['Current password'][st.session_state.language], 'New password': labels['New password'][st.session_state.language], 'Repeat password': labels['Repeat password'][st.session_state.language], 'Reset': labels['Reset'][st.session_state.language]}):
        st.success(labels['Change success'][st.session_state.language])
        time.sleep(3)
        update_yaml_file()
        st.session_state.page = "chatbot"
        st.rerun()

def get_uploaded_files():
    uploaded_files = st.sidebar.file_uploader(
        "NONE",
        accept_multiple_files=True,
        label_visibility="hidden",
        key=st.session_state.file_uploader_key
    )
    return uploaded_files

def show_history_page():
    labels = {
        'Go back': {'English': 'Go back', 'Korean': '돌아가기'},
        'Current conversation': {'English': 'Current conversation', 'Korean': '현재 대화'},
        'Save conversation': {'English': 'Save conversation', 'Korean': '대화 저장'},
        'Conversation name': {'English': 'Enter a name for the conversation to save.', 'Korean': '저장할 대화 이름을 입력하세요.'},
        'Save': {'English': 'Save', 'Korean': '저장'},
        'Past conversations': {'English': 'Past conversations', 'Korean': '과거 대화'},
        'Select conversation': {'English': 'Select a conversation.', 'Korean': '대화를 선택해주세요.'},
        'Load': {'English': 'Load', 'Korean': '불러오기'},
        'Delete': {'English': 'Delete', 'Korean': '삭제하기'}
    }
    if "file_uploader_key" in st.session_state:
        uploaded_files = get_uploaded_files()
    if st.sidebar.button(labels['Go back'][st.session_state.language]):
        st.session_state.page = "chatbot"
        st.rerun()
    if not os.path.isdir("./users"):
        os.mkdir("./users")
    if not os.path.isdir(f"./users/{st.session_state.username}"):
        os.mkdir(f"./users/{st.session_state.username}")
    st.header(labels['Current conversation'][st.session_state.language])
    with st.form(labels['Save conversation'][st.session_state.language], clear_on_submit=True):
        file_name = st.text_input(labels['Conversation name'][st.session_state.language])
        submitted = st.form_submit_button(labels['Save'][st.session_state.language])
        if submitted:
            data = []
            for container in st.session_state.containers:
                data.append([container.role, container.blocks])
            with open(f"./users/{st.session_state.username}/{file_name}.pkl", 'wb') as f:
                pickle.dump(data, f)
    st.header(labels['Past conversations'][st.session_state.language])
    files = os.listdir(f"./users/{st.session_state.username}")
    files = [x for x in files if x.endswith('.pkl')]
    options = [x.replace('.pkl', '') for x in files]
    option = st.selectbox(labels['Select conversation'][st.session_state.language], options)
    col1, col2 = st.columns((1, 6))
    with col1:
        if option is not None and st.button(labels['Load'][st.session_state.language]):
            delete_messages()
            st.session_state.containers = []
            with open(f"./users/{st.session_state.username}/{option}.pkl", 'rb') as f:
                data = pickle.load(f)
                for x in data:
                    role = x[0]
                    blocks = x[1]
                    container = Container(role, blocks)
                    st.session_state.containers.append(container)
                    create_message(role, container.get_content())
            st.session_state.page = "chatbot"        
            st.rerun()
    with col2:
        if option is not None and st.button(labels['Delete'][st.session_state.language]):
            os.remove(f"./users/{st.session_state.username}/{option}.pkl")
            st.rerun()

def handle_files():
    supported_files = {
        "file_search": ['.c', '.cs', '.cpp', '.doc', '.docx', '.html', '.java', '.json', '.md', '.pdf', '.php', '.pptx', '.py', '.rb', '.texv', '.txt', '.css', '.js', '.sh', '.ts'],
        "code_interpreter": ['.c', '.cs', '.cpp', '.doc', '.docx', '.html', '.java', '.json', '.md', '.pdf', '.php', '.pptx', '.py', '.rb', '.tex', '.txt', '.css', '.js', '.sh', '.ts', '.csv', '.jpeg', '.jpg', '.gif', '.png', '.tar', '.xlsx', '.xml', '.zip']
    }

    uploaded_files = get_uploaded_files()

    for uploaded_file in uploaded_files:
        upload_id = uploaded_file.file_id
        file_name = uploaded_file.name
        if upload_id in st.session_state.upload_ids:
            continue
        with tempfile.TemporaryDirectory() as t:
            file_path = os.path.join(t, file_name)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            add_message("user", f"파일 업로드: `{file_name}`")
            if file_name.endswith(".jpg") or file_name.endswith(".png") or file_name.endswith(".jpeg"):
                file = st.session_state.client.files.create(file=Path(file_path), purpose="vision")
                content=[
                    {"type": "text", "text": f"파일 업로드: `{file_name}`"},
                    {"type": "image_file", "image_file": {"file_id": file.id}}
                ]
                create_message("user", content)
            else:
                file = st.session_state.client.files.create(file=Path(file_path), purpose="assistants")
                tools = []
                if file_name.endswith(tuple(supported_files["file_search"])):
                    tools.append({"type": "file_search"})
                if file_name.endswith(tuple(supported_files["code_interpreter"])):
                    tools.append({"type": "code_interpreter"})
                if not tools:
                    tools.append({"type": "code_interpreter"})
                attachments = [{"file_id": file.id, "tools": tools}]
                content=[{"type": "text", "text": f"파일 업로드: `{file_name}`"}]
                create_message("user", content, attachments)
            st.session_state.upload_ids[upload_id] = {'file_id': file.id, 'file_name': file_name}

    for upload_id, upload_data in list(st.session_state.upload_ids.items()):
        file_name = upload_data["file_name"]
        file_id = upload_data["file_id"]
        if upload_id not in [x.file_id for x in uploaded_files]:
            st.session_state.client.files.delete(file_id)
            add_message("user", f"파일 삭제: `{file_name}`")
            del st.session_state.upload_ids[upload_id]

def list_messages():
    messages = st.session_state.client.beta.threads.messages.list(
        thread_id=st.session_state.thread.id
    )
    return messages

def delete_messages():
    messages = list_messages()
    for message in messages.data:
        deleted_message = st.session_state.client.beta.threads.messages.delete(
            thread_id=st.session_state.thread.id,
            message_id=message.id
        )

def create_message(role, content, attachments=None):
    """
    Create a message and add it to the thread.
    """
    if not is_thread_locked():
        st.session_state.client.beta.threads.messages.create(
            thread_id=st.session_state.thread.id,
            role=role,
            content=content,
            attachments=attachments
        )

def delete_files():
    """
    Delete all files uploaded to OpenAI.
    """
    for upload_id, upload_data in st.session_state.upload_ids.items():
        st.session_state.client.files.delete(upload_data["file_id"])

def list_runs(limit=100):
    """
    Returns a list of runs belonging to the thread.
    """
    runs = st.session_state.client.beta.threads.runs.list(
        thread_id=st.session_state.thread.id,
        limit=limit
    )
    return runs

def is_thread_locked():
    """
    Returns whether the thread is locked.
    """
    return len([x for x in list_runs().data if x.status in ["queued", "in_progress"]]) > 0