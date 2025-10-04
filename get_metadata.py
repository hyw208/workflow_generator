import requests
import xml.etree.ElementTree as ET

def get_user_task_extension_metadata(process_instance_id, camunda_base_url="http://localhost:8080/engine-rest"):
    """
    Retrieves the extension metadata for the first active user task in a given process instance.

    Args:
        process_instance_id: The ID of the running process instance.
        camunda_base_url: The base URL of the Camunda REST API.

    Returns:
        A dictionary containing the key-value pairs of the extension metadata,
        or None if not found or an error occurs.
    """
    try:
        # 1. Get the process definition ID from the process instance
        instance_url = f"{camunda_base_url}/process-instance/{process_instance_id}"
        instance_response = requests.get(instance_url)
        instance_response.raise_for_status()  # Raise an exception for bad status codes
        definition_id = instance_response.json().get("definitionId")

        if not definition_id:
            print(f"Error: Could not find definitionId for process instance {process_instance_id}")
            return None

        # 2. Find the active user task to get its taskDefinitionKey
        task_url = f"{camunda_base_url}/task?processInstanceId={process_instance_id}"
        task_response = requests.get(task_url)
        task_response.raise_for_status()
        tasks = task_response.json()

        if not tasks:
            print(f"Error: No active user tasks found for process instance {process_instance_id}")
            return None
        
        # Assuming we're interested in the first user task found
        task_definition_key = tasks[0].get("taskDefinitionKey")

        if not task_definition_key:
            print("Error: Could not find taskDefinitionKey for the active task.")
            return None

        # 3. Get the BPMN XML from the process definition
        xml_url = f"{camunda_base_url}/process-definition/{definition_id}/xml"
        xml_response = requests.get(xml_url)
        xml_response.raise_for_status()
        bpmn_xml_string = xml_response.json().get("bpmn20Xml")

        if not bpmn_xml_string:
            print(f"Error: Could not retrieve BPMN XML for definition {definition_id}")
            return None

        # 4. Parse the XML and extract the metadata
        root = ET.fromstring(bpmn_xml_string)
        namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'camunda': 'http://camunda.org/schema/1.0/bpmn'
        }

        # Find the specific userTask using its ID (taskDefinitionKey)
        user_task_element = root.find(f".//bpmn:userTask[@id='{task_definition_key}']", namespaces)

        if user_task_element is None:
            print(f"Error: Could not find userTask with ID '{task_definition_key}' in the BPMN XML.")
            return None

        # Find the extensionElements and then the camunda:meta tags
        metadata = {}
        extension_elements = user_task_element.find('bpmn:extensionElements', namespaces)
        if extension_elements is not None:
            for meta_element in extension_elements.findall('camunda:meta', namespaces):
                key = meta_element.get('key')
                value = meta_element.text
                if key:
                    metadata[key] = value
        
        return metadata

    except requests.exceptions.RequestException as e:
        print(f"An HTTP error occurred: {e}")
        return None
    except ET.ParseError as e:
        print(f"An XML parsing error occurred: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# --- Example Usage ---

# The process instance ID from our conversation
process_id = "38ab5183-a01e-11f0-988a-0242ac110002"

# Get the metadata
metadata = get_user_task_extension_metadata(process_id)

if metadata:
    print("\nSuccessfully retrieved user task extension metadata:")
    print(metadata)
else:
    print("\nFailed to retrieve metadata.")
