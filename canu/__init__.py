import yaml
import streamlit as st
import streamlit_authenticator as stauth
import openai

class Container():
    def __init__(self, role, blocks):
        self.container = st.empty()
        self.role = role
        self.blocks = blocks

    def _write_blocks(self):
        with st.chat_message(self.role):
            for block in self.blocks:
                if block['type'] == 'text':
                    st.write(block['content'], unsafe_allow_html=True)
                elif block['type'] == 'code':
                    st.code(block['content'])
                elif block['type'] == 'image':
                    st.image(block['content'])

    def write_blocks(self, stream=False):
        if stream:
            with self.container:
                self._write_blocks()
        else:
            self._write_blocks()

class EventHandler(openai.AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.container = None

    def on_text_delta(self, delta, snapshot):
        if self.container is None:
            self.container = Container("assistant", [])
        if not self.container.blocks or self.container.blocks[-1]['type'] != 'text':
            self.container.blocks.append({'type': 'text', 'content': ""})
        if delta.annotations is not None:
            for annotation in delta.annotations:
                if annotation.type == "file_citation":
                    cited_file = st.session_state.client.files.retrieve(annotation.file_citation.file_id)
                    delta.value = delta.value.replace(annotation.text, f"""<a href="#" title="{cited_file.filename}">[❞]</a>""")
        self.container.blocks[-1]["content"] += delta.value
        self.container.write_blocks(stream=True)

    def on_image_file_done(self, image_file):
        if self.container is None:
            self.container = canu.Container("assistant", [])
        if not self.container.blocks or self.container.blocks[-1]['type'] != 'image':
            self.container.blocks.append({'type': 'image', 'content': ""})
        image_data = st.session_state.client.files.content(image_file.file_id)
        image_data_bytes = image_data.read()
        self.container.blocks[-1]["content"] = image_data_bytes
        self.container.write_blocks(stream=True)

    def on_end(self):
        if self.container is not None:
            st.session_state.containers.append(self.container)

def get_authenticator(yaml_file):
    with open(yaml_file) as f:
        config = yaml.load(f, Loader=yaml.loader.SafeLoader)
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
    )
    return authenticator

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

def logout():
    st.session_state.authenticator.logout(location='unrendered')