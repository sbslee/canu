import yaml
import streamlit as st
import streamlit_authenticator as stauth

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