import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000, chunk_overlap=1000
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_texts(
            texts=text_chunks,
            embedding=embeddings,
        )
        vector_store.save_local("faiss_index")
        return vector_store
    except Exception as e:
        st.error(f"Erro ao criar vetor: {str(e)}")
        return None


def get_conversational_chain():

    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

    return chain


def user_input(user_question):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        # Tente carregar o vetor com deserialização permitida
        new_db = FAISS.load_local(
            folder_path="faiss_index",
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )

        docs = new_db.similarity_search(user_question)
        chain = get_conversational_chain()

        response = chain(
            {"input_documents": docs, "question": user_question},
            return_only_outputs=True,
        )

        print(response)
        st.write("Reply: ", response["output_text"])
    except Exception as e:
        st.error(f"Erro ao processar a pergunta: {str(e)}")


def main():
    st.set_page_config("Chat PDF")
    st.header("AS05 - 688875 - Tópicos III - Chat leitor de PDF com Gemini")

    st.markdown(
        "<h1 style='text-align: center;'>Menu:</h1>", unsafe_allow_html=True
    )

    # Criar container para área de upload e processamento
    upload_container = st.container()

    with upload_container:
        pdf_docs = st.file_uploader(
            "Carregar arquivos PDF e clicar no botão 'Enviar e Processar'",
            accept_multiple_files=True,
        )

        # Gerenciamento de estado para processamento do PDF
        if "pdf_processed" not in st.session_state:
            st.session_state.pdf_processed = False

        if st.button("Enviar e Processar") and pdf_docs:
            with st.spinner("Processando..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.session_state.pdf_processed = True
            st.success("Concluído")

    # Criar container separado para área de perguntas
    question_container = st.container()

    with question_container:
        user_question = st.text_input(
            "Perguntar sobre o PDF",
            disabled=not st.session_state.pdf_processed,
        )

        if not st.session_state.pdf_processed:
            st.info(
                "⚠️ Por favor, carregue e processe um arquivo PDF primeiro para habilitar as perguntas"
            )
        elif user_question:
            with st.spinner("Encontrando resposta..."):
                user_input(user_question)


if __name__ == "__main__":
    main()