# Import necessary libraries and modules
import os
import requests
import json
from dotenv import load_dotenv
import streamlit as st
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from typing import Optional, Type
from langchain_community.chat_models import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.messages import HumanMessage
from langchain.agents import create_tool_calling_agent
from langchain import hub
from langchain.agents import AgentExecutor
from langchain_openai.chat_models import AzureChatOpenAI
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)


# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables using os.getenv
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL")

# Option 1: use an OpenAI account
# EMBEDDED_ASSISTANT_API_KEY="a262fb9c71214ab7973fcc63f8ee23e4"
# EMBEDDED_ASSISTANT_API_ENDPOINT="https://rsopenaitesteastus.openai.azure.com/"
# EMBEDDED_ASSISTANT_MODEL="text-embedding-3-small"

openai_embedded_api_endpoint: str = os.getenv("EMBEDDED_ASSISTANT_API_ENDPOINT")
openai_embedded_api_key: str = os.getenv("EMBEDDED_ASSISTANT_API_KEY")
openai_embedded_api_version: str = "2024-02-01"
embedded_model: str = os.getenv("EMBEDDED_ASSISTANT_MODEL")

# AZURE_AI_SEARCH_ENDPOINT="https://reportaisearch.search.windows.net"
# AZURE_AI_SEARCH_API_KEY=""
# AZURE_AI_SEARCH_INDEX="reportsearchnew"

vector_store_address: str = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
vector_store_password: str = os.getenv("AZURE_AI_SEARCH_API_KEY")
index_name: str = os.getenv("AZURE_AI_SEARCH_INDEX")

def get_report_content_from_api(patientid = 1517):
    
    url = f"https://team-maven-fhir-apim.azure-api.net/fhir/DiagnosticReport?_count=50&page=1&subject={patientid}&_dc=1716314695586"

    payload = {}
    headers = {
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjJCQUNDQzE4NzA5MUJERDlDNjgzRUMzMUQ2QzMzODhEMTc1RURDRkYiLCJ4NXQiOiJLNnpNR0hDUnZkbkdnLXd4MXNNNGpSZGUzUDgiLCJ0eXAiOiJKV1QifQ.eyJjbGllbnRJUCI6Ijk5LjIzOC4xNDYuMjM2IiwidGlkIjoiYWYzODJmMzEtNjc5OS00NTg1LWExMTMtYjVkMzg3ZmE1MmVlIiwibmFtZSI6IlRvbSBDaGVuIiwiZW1haWwiOiJ0Y2hlbkByYW1zb2Z0LmNvbSIsInByZWZlcnJlZF91c2VybmFtZSI6InRjaGVuQHJhbXNvZnQuY29tIiwiaWRwIjoicmFtc29mdC5jb20iLCJleHRlbnNpb25faWRwX2RvbWFpbiI6InJhbXNvZnQuY29tIiwiaWRwX3R5cGUiOiJBQUQiLCJpZHBHcm91cE1lbWJlcnNoaXBzIjpbIk1pY3Jvc29mdCAzNjUgRTUgQ29tcGxpYW5jZSIsIk1hdmVuIFRlYW0gU0ciLCJNaWNyb3NvZnQgMzY1IEUzIiwiT0FJIFBST0QgVVNFUlMgUlcgQVpVUkUgU0ciLCJPbWVnYSBBSSBSVyBTRyIsIlNWTiBSZWFkLVdyaXRlIFVzZXJzIFNHIiwiU2FsZXNmb3JjZSBVc2VycyBTRyIsIlByb2QgT21lZ2EgQUkgUlcgU0ciLCJDb25mbHVlbmNlIFVzZXJzIFNHIiwiUHJvZCBPbWVnYSBBSSBSYW1zb2Z0IEludGVybmFsIiwiU1ZOIiwiUGV0YWRhdGEgUlcgU0ciLCJTbGFjayBVc2VycyBTRyIsIkRldiBPQUkgUHJvZCBVc2VycyBSVyBBcHAgU0ciLCJEZXZlbG9wbWVudCBQcml2aWxlZ2VkIFVzZXJzIFNHIiwiUmFtU29mdCBJbnR1bmUgU0ciLCJGaWdtYSBVc2VycyBTRyIsIk1pY3Jvc29mdCAzNjUgRTUgU2VjdXJpdHkiLCJKaXJhIFVzZXJzIFNHIiwiUHJlUHJvZCBPbWVnYSBBSSBSYW1zb2Z0IEludGVybmFsIiwiRGV2ZWxvcG1lbnQgU0ciLCJEZXZlbG9wbWVudCBTZWN1cml0eSBHcm91cCIsIlBpbG90IFVzZXJzIFNHIiwiUHJlUHJvZCBPbWVnYSBBSSBSVyBTRyIsIkFsbCBFbXBsb3llZXMgU0ciLCJQb3dlciBCSSBQcm8iLCJJbnR1bmUgVXNlcnMgU0ciXSwiZXh0ZW5zaW9uX1Bob25lTnVtYmVyTGlzdCI6IiIsImV4dGVuc2lvbl9Ob3RpZmljYXRpb25FbWFpbExpc3QiOiIiLCJzdWIiOiIzZTgyNWE2Mi1mYmZhLTRjM2EtOWJiZS05MjZjMWU2YzIzNTEiLCJvaWQiOiIzZTgyNWE2Mi1mYmZhLTRjM2EtOWJiZS05MjZjMWU2YzIzNTEiLCJnaXZlbl9uYW1lIjoiVG9tIiwiZmFtaWx5X25hbWUiOiJDaGVuIiwiaXNGb3Jnb3RQYXNzd29yZCI6ZmFsc2UsImttc2kiOiJGYWxzZSIsIm5vbmNlIjoiMGFhNzlmNTgtNTAxMy00MzIxLThhZGItMTRjOTdlYmI1NGNhIiwic2NwIjoidXNlcl9pbXBlcnNvbmF0aW9uIiwiYXpwIjoiYTE5YzRkOWItZGVjNS00NzI0LTgwMWItYzVlMzA1ZGI1Zjc3IiwidmVyIjoiMS4wIiwiaWF0IjoxNzE2Mzg1NTgyLCJhdWQiOiIyMjZkYTg4YS1lMDY1LTRlMzAtODUzYS1lNjgxMDM2MDk2ZjMiLCJleHAiOjE3MTYzODkxODIsImlzcyI6Imh0dHBzOi8vcnNiMmN0ZW5hbnQuYjJjbG9naW4uY29tL2MwOGE1Nzc0LTc3ZmYtNDA2NC1iYjQyLWJmNzk4MDc5NDM3Mi92Mi4wLyIsIm5iZiI6MTcxNjM4NTU4Mn0.MKFXfNZVoIEch7zY2i1kkI1-53dfe-BdfPUXm8CzHSu_AHpV8ITFU25AwSiRUXR3IdMdRuvHrP6u7Q627kND-GeB-Uhk4vnuPa1BMYnRHgboI6f3s0ATVYiv-Yb5p7Pl7l06xcw4zIy2HlZmj9bOYaSxWGpqqcxEAPIKljg4lth31y6OhggrhmaxV2yjwYgA5aV7AcarjV1IEVIRj_YYZRd-Ngebq0HNd3MygqgAMmhjOtt5QiUkKECnZH4qsHa0xSGJcB8Rbgg6HNx-99jLK-oMWjc8t7BHU8EmH1KoesqThYNrOlZEPagNWyyUjeSGxXU0bZxXwifAb1SG4P9NcA'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)

    #get all ids from response
    data = json.loads(response.text)

    result = []
    for entry in data['entry']:
        id = entry['resource']['id']

        url = f"https://team-maven-fhir-apim.azure-api.net/fhir/DiagnosticReport/{id}/ReportContent?_dc=4044174&originalform=true"
        response = requests.get(url, headers=headers, data=payload)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        cleaned_text = text.replace('â', '')  # replace unwanted characters with nothing
        cleaned_text = cleaned_text.replace('\x80', '')
        cleaned_text = cleaned_text.replace('\xa0', '')
        cleaned_text = cleaned_text.replace('¯', '')
        result.append(cleaned_text)
    return result
    print(result)
    
def get_report_content_from_local(patientid = 1517):
    result = ['Patient:John Doe, 58-year-old maleModality:PET-CT Whole BodyClinical History:History of hepatocellular carcinoma with known metastatic disease to lungs and bones, undergoing staging evaluation.Findings:Head and Neck:No abnormal FDG uptake is identified in the brain, suggestive of no intracranial metastatic disease. The salivary glands and thyroid gland exhibit normal FDG uptake patterns. No hypermetabolic cervical lymphadenopathy or masses are seen.Chest:Multiple hypermetabolic lesions are identified in both lungs, consistent with known metastatic disease. The largest lesion is in the right upper lobe, with a standardized uptake value (SUV) of 8.5. Multiple mediastinal and hilar lymph nodes demonstrate increased FDG uptake, with the highest SUV of 7.2 noted in the subcarinal lymph node, consistent with metastatic involvement.Abdomen and Pelvis:The liver is significantly enlarged with multiple hypermetabolic lesions throughout, the largest in segment VIII with an SUV of 12.7, consistent with known hepatocellular carcinoma. There is increased FDG uptake in the spleen with an SUV of 5.6, suggestive of potential metastatic involvement. The gallbladder appears unremarkable. No hypermetabolic lesions are seen in the pancreas or adrenal glands. There is no abnormal FDG uptake in the bowel.Skeleton:Multiple hypermetabolic lytic lesions are present in the spine, ribs, and sternum, consistent with metastatic disease. The highest SUV of 9.0 is observed in the T8 vertebral body. Additional hypermetabolic bone lesions are identified in the pelvis, with an SUV of 7.8 in the right iliac crest and 6.4 in the left sacrum.Soft Tissues:No abnormal FDG uptake is identified in the soft tissues or muscles.Impression:Multiple hypermetabolic lesions in the lungs and mediastinal/hilar lymph nodes, consistent with metastatic disease.Hypermetabolic lesions in the liver, consistent with known hepatocellular carcinoma.Hypermetabolic lesions in the spleen, suggestive of potential metastatic involvement.Multiple hypermetabolic bone lesions in the spine, ribs, sternum, and pelvis, consistent with metastatic disease.The findings are consistent with widespread metastatic disease from hepatocellular carcinoma. The patient would benefit from further evaluation by the oncology team to determine the best course of systemic therapy or palliative care.',
 ' Patient:John Doe, 58-year-old maleModality:CT Chest with ContrastClinical History:History of hepatitis C with known hepatocellular carcinoma, presenting with weight loss and shortness of breath.Findings:Lungs:Multiple scattered pulmonary nodules are identified in both lungs, the largest measuring 2.1 cm in the right upper lobe, with some demonstrating cavitation. There is no evidence of significant consolidation or ground-glass opacity to suggest pneumonia or other acute inflammatory processes. No pleural effusion or pneumothorax is seen.Mediastinum and Lymph Nodes:Enlarged mediastinal and hilar lymph nodes are noted, with the largest lymph node measuring 1.8 cm in the subcarinal region. Additional enlarged lymph nodes are present in the right paratracheal, aortopulmonary, and bilateral hilar regions, with sizes ranging from 1.0 to 1.5 cm in short-axis diameter.Heart and Great Vessels:The heart is normal in size with no evidence of pericardial effusion. The thoracic aorta is of normal caliber with no evidence of aneurysm or dissection. The pulmonary arteries are patent, with no signs of pulmonary embolism.Bones:There is evidence of diffuse osteopenia. Multiple lytic lesions are seen in the thoracic spine, ribs, and sternum, suggestive of metastatic disease. The largest lesion is located in the T8 vertebral body, measuring 1.5 cm, with mild cortical thinning.Soft Tissues:No significant soft tissue abnormalities or masses are identified. The visualized portion of the upper abdomen reveals an enlarged liver with nodular contour and multiple hypodense lesions, consistent with the known history of cirrhosis and hepatocellular carcinoma.Impression:Multiple pulmonary nodules, some cavitating, concerning for metastatic disease.Enlarged mediastinal and hilar lymph nodes, also concerning for metastatic involvement.Multiple lytic bone lesions in the thoracic spine, ribs, and sternum, consistent with metastatic disease.No evidence of acute pneumonia, pleural effusion, or pneumothorax.No evidence of pulmonary embolism.Overall, the findings are consistent with advanced metastatic disease from a primary hepatocellular carcinoma. Further evaluation by oncology is recommended for potential systemic therapy or palliative care.',
 ' Patient:John Doe, 58-year-old maleModality:MRI Abdomen with ContrastClinical History:History of hepatitis C, presenting with weight loss, jaundice, and elevated liver enzymes.Findings:Liver:The liver is significantly enlarged, measuring approximately 22 cm in craniocaudal dimension, with a nodular contour suggestive of cirrhosis. Multiple irregularly shaped lesions are noted throughout the hepatic parenchyma with varying signal characteristics on T1- and T2-weighted images. The largest lesion is located in segment VIII, measuring 4.5 cm in greatest dimension, and demonstrates heterogeneous enhancement on post-contrast imaging, with early arterial phase hyperenhancement and subsequent washout in the portal venous phase, suggestive of hepatocellular carcinoma (HCC). Additional lesions exhibiting similar imaging characteristics are found in segments II, IV, and VI, measuring 3.8 cm, 2.5 cm, and 2.0 cm in diameter, respectively.Bile Ducts:The intrahepatic bile ducts are mildly dilated, especially in the left lobe, with the common bile duct measuring 9 mm in diameter, indicative of mild biliary obstruction. There is no evidence of choledocholithiasis or intrahepatic duct stones.Gallbladder:The gallbladder is contracted and contains multiple calculi with posterior acoustic shadowing. The gallbladder wall is thickened, measuring up to 5 mm, consistent with chronic cholecystitis. There is no pericholecystic fluid or evidence of acute inflammation.Pancreas:The pancreas is unremarkable in size and signal intensity. No focal pancreatic lesions or ductal dilatation is identified. The pancreatic duct measures 2 mm, which is within normal limits.Spleen:The spleen is slightly enlarged, measuring 14 cm in craniocaudal dimension. It exhibits homogeneous signal intensity, and no focal splenic lesions are identified.Adrenal Glands:The bilateral adrenal glands appear normal in size and morphology, with no evidence of masses or hyperplasia.Vasculature:The portal vein is patent, with no evidence of thrombosis. The hepatic veins are also patent, with no signs of Budd-Chiari syndrome. The inferior vena cava is within normal limits.Impression:Significant hepatomegaly with nodular contour consistent with cirrhosis.Multiple hepatic lesions with imaging characteristics suggestive of hepatocellular carcinoma (HCC), the largest measuring 4.5 cm in segment VIII.Mild biliary obstruction with intrahepatic ductal dilation and a common bile duct measuring 9 mm.Chronic cholecystitis with gallstones.Mild splenomegaly.Recommendations include correlation with clinical and laboratory findings, as well as potential biopsy of liver lesions for histopathologic confirmation. Further assessment by a multidisciplinary team is recommended for appropriate management planning, including potential liver transplantation evaluation. ']
    return result

def get_report_content():
    #return get_report_content_from_api()
    return get_report_content_from_local()


llm = AzureChatOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_deployment=os.environ["OPENAI_CHAT_MODEL"],
    streaming=True,
)

class PatientReportSearchTool(BaseTool):
    name = "patient_report_search_tool"
    description = "useful to retrieve patient reports data"

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return get_report_content()

    async def _arun(
        self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")

tools = [PatientReportSearchTool()]


# Define Streamlit app
def app():
    st.set_page_config(
        page_title="Report AI Search",
        page_icon="🧊",
    )
    # Set the title and logo of the Streamlit app
    st.title("Report AI Search POC")
    #st.image("https://biendata.xyz/media/7c92a358-84ff-4d88-b44b-33861780b703_logo.png", use_column_width=True)
    st.image("banner2.png", use_column_width=True)
    
    # Prompt the user to enter a question and provide a text input field
    st.write("Patient ID: 1517")
    st.write("Enter your question below and click 'Submit' to get an answer.")
    question = st.text_input("Question:")
    from langchain.prompts import MessagesPlaceholder
    # When the user clicks the "Submit" button, generate a response using the SQL database agent
    if st.button("Submit"):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", 
                 """
                 "You are a helpful assistant for radiologists.You will use patient search tool to provide details of patient reports. You will not ask for more information.",
                 """
                ),
                ("user", f"{question}\n ai: "),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ]
        )
        
        agent = create_tool_calling_agent(llm, tools, prompt)

        # Create an agent executor by passing in the agent and tools
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        response = agent_executor.invoke({"input":  question})
                
        # Display the response in the Streamlit app's output area
        st.write("Output:")
        st.write(response['output'])

# Run the Streamlit app
if __name__ == "__main__":
    app()
