import os, time, yaml, pickle, tempfile, base64
from pathlib import Path
import streamlit as st
import streamlit_authenticator as stauth
import openai

class Container():
    def __init__(self, role, blocks):
        self.container = st.empty()
        self.role = role
        self.blocks = blocks
        self.code_interpreter_files = {}

    def _write_blocks(self):
        with st.chat_message(self.role):
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
                    else:
                        mime = "text/plain"
                    st.download_button(
                        label=f"{filename}",
                        data=content,
                        file_name=filename,
                        mime=mime
                    )

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
    st.session_state.client.beta.threads.messages.create(
        thread_id=st.session_state.thread.id,
        role=role,
        content=content
    )
    st.session_state.containers.append(
        Container(role, [{'type': 'text', 'content': content}])
    )

def write_stream(event_handler=None):
    if event_handler is None:
        event_handler = EventHandler()
    with st.session_state.client.beta.threads.runs.stream(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
        event_handler=event_handler,
    ) as stream:
        stream.until_done()

def show_login_page():
    st.session_state.name, st.session_state.authentication_status, st.session_state.username = st.session_state.authenticator.login(location="main", fields={'Form name':'로그인', 'Username':'아이디', 'Password':'비밀번호', 'Login':'로그인'})
    if st.session_state.authentication_status:
        st.session_state.page = "chatbot"
        st.rerun()
    elif st.session_state.authentication_status is False:
        st.error("아이디 또는 비밀번호가 잘못되었습니다.")
    elif st.session_state.authentication_status is None:
        pass

def show_profile_page():
    if "file_uploader_key" in st.session_state:
        uploaded_files = get_uploaded_files()
    if st.button("돌아가기"):
        st.session_state.page = "chatbot"
        st.rerun()
    if st.session_state.authenticator.reset_password(st.session_state.username, fields={'Form name':'비밀번호 변경', 'Current password':'현재 비밀번호', 'New password':'새로운 비밀번호', 'Repeat password': '새로운 비밀번호 확인', 'Reset':'변경'}):
        st.success("비밀번호가 성공적으로 변경되었습니다.")
        time.sleep(3)
        update_yaml_file()
        st.session_state.page = "chatbot"
        st.rerun()

def get_uploaded_files():
    uploaded_files = st.sidebar.file_uploader(
        "파일 업로드",
        accept_multiple_files=True,
        key=st.session_state.file_uploader_key
    )
    return uploaded_files

def show_history_page():
    if "file_uploader_key" in st.session_state:
        uploaded_files = get_uploaded_files()
    if st.button("돌아가기"):
        st.session_state.page = "chatbot"
        st.rerun()
    if not os.path.isdir("./users"):
        os.mkdir("./users")
    if not os.path.isdir(f"./users/{st.session_state.username}"):
        os.mkdir(f"./users/{st.session_state.username}")
    st.header("현재 이 대화를 저장하고 싶다면:")
    with st.form("대화 저장", clear_on_submit=True):
        file_name = st.text_input("저장할 대화 이름을 입력하세요.")
        submitted = st.form_submit_button("저장")
        if submitted:
            data = []
            for container in st.session_state.containers:
                data.append([container.role, container.blocks])
            with open(f"./users/{st.session_state.username}/{file_name}.pkl", 'wb') as f:
                pickle.dump(data, f)
    st.header("과거에 저장한 대화를 불러오려면:")
    files = os.listdir(f"./users/{st.session_state.username}")
    files = [x for x in files if x.endswith('.pkl')]
    st.write(f"{len(files)}개의 대화가 저장되어 있습니다.")
    options = [x.replace('.pkl', '') for x in files]
    option = st.selectbox("불러올 대화를 선택해주세요.", options)
    if option is not None and st.button("불러오기"):
        st.session_state.containers = []
        with open(f"./users/{st.session_state.username}/{option}.pkl", 'rb') as f:
            data = pickle.load(f)
            for container in data:
                st.session_state.containers.append(Container(container[0], container[1]))
        st.session_state.page = "chatbot"
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
                st.session_state.client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id,
                    role="user",
                    content=content,
                )
            else:
                file = st.session_state.client.files.create(file=Path(file_path), purpose="assistants")
                tools = []
                if file_name.endswith(tuple(supported_files["file_search"])):
                    tools.append({"type": "file_search"})
                if file_name.endswith(tuple(supported_files["code_interpreter"])):
                    tools.append({"type": "code_interpreter"})
                attachments = [{"file_id": file.id, "tools": tools}]
                content=[{"type": "text", "text": f"파일 업로드: `{file_name}`"}]
                st.session_state.client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id,
                    role="user",
                    content=content,
                    attachments=attachments,
                )
            st.session_state.upload_ids[upload_id] = {'file_id': file.id, 'file_name': file_name}

    for upload_id, upload_data in list(st.session_state.upload_ids.items()):
        file_name = upload_data["file_name"]
        file_id = upload_data["file_id"]
        if upload_id not in [x.file_id for x in uploaded_files]:
            st.session_state.client.files.delete(file_id)
            add_message("user", f"파일 삭제: `{file_name}`")
            del st.session_state.upload_ids[upload_id]