import json
import yaml
from xml.dom import minidom
import xml.etree.ElementTree as ET
import pandas as pd

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
OMGDC_NS = "http://www.omg.org/spec/DD/20100524/DC"
OMGDI_NS = "http://www.omg.org/spec/DD/20100524/DI"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace('', BPMN_NS)
ET.register_namespace('camunda', CAMUNDA_NS)
ET.register_namespace('bpmndi', BPMNDI_NS)
ET.register_namespace('omgdc', OMGDC_NS)
ET.register_namespace('omgdi', OMGDI_NS)     
ET.register_namespace('xsi', XSI_NS) 

class Workflow:
    """
        <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                     xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC"
                     xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI"
                     xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                     targetNamespace="http://bpmn.io/schema/bpmn"
                     id="Definitions_1">
            ...
    """
    def __init__(self, id="Definitions_1", name=None, target_namespace="http://bpmn.io/schema/bpmn"):
        self.name = name
        self.root = ET.Element(f"{{{BPMN_NS}}}definitions", {
            f"xmlns:xsi": XSI_NS,
            f"xmlns:bpmndi": BPMNDI_NS,
            f"xmlns:omgdc": OMGDC_NS,
            f"xmlns:omgdi": OMGDI_NS,
            "targetNamespace": target_namespace,
            "id": id
        })

    def add_error(self, error):
        self.root.append(error.element)

    def add_process(self, process):
        self.root.append(process.element)
    
    def to_pretty_xml(self):
        rough_string = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def to_xml(self, filename):
        to_pretty_xml = self.to_pretty_xml()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(to_pretty_xml)

class Error:
    """
        <error id="REJECTION_ERROR" name="Rejection Error" errorCode="REJECTION_ERROR" />
    """
    def __init__(self, id, name, error_code):
        attribs = {"id": id, "name": name, "errorCode": error_code}
        self.element = ET.Element(f"{{{BPMN_NS}}}error", attrib=attribs)

class Process:
    """
        <process id="Process_1" isExecutable="true" camunda:historyTimeToLive="180">
            ...
        </process>
    """
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        self.id = id
        self.element = ET.Element(
            f"{{{BPMN_NS}}}process",
            id=id,
            isExecutable=str(is_executable).lower(),
            **{f"{{{CAMUNDA_NS}}}historyTimeToLive": history_ttl}
        )
        self.elements = {}

    def _add_element(self, element, elem_id):
        self.elements[elem_id] = element

    def add_sequence_flow(self, id, source_ref, target_ref):
        return ET.SubElement(self.element, f"{{{BPMN_NS}}}sequenceFlow", id=id, sourceRef=source_ref, targetRef=target_ref)

class StartEvent:
    """
        <startEvent id="StartEvent_1" />
    """
    def __init__(self, process, id="StartEvent_1", seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}startEvent", id=id)
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class EndEvent:
    """
        <endEvent id="EndEvent_1">
            <errorEventDefinition errorRef="REJECTION_ERROR" />
        </endEvent>
    """
    def __init__(self, process, id="EndEvent_1", errorRef=None, seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}endEvent", id=id)
        if errorRef:    
            ET.SubElement(self.element, f"{{{BPMN_NS}}}errorEventDefinition", errorRef=errorRef)
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class UserTask:
    """
        <userTask id="UserTask_1" name="Approval Task" camunda:assignee="john.doe">
            <extensionElements>
                <camunda:meta key="priority">high</camunda:meta>
                <camunda:meta key="dueDate">2024-12-31T23:59:59</camunda:meta>
            </extensionElements>
        </userTask>
    """
    def __init__(self, process, id, name, config=None, meta=None, seq=None, next=None):
        config = parse_config_meta_next(config)
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}userTask", id=id, name=name, **(config if config else {{}}))
        
        meta = parse_config_meta_next(meta)
        if meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for key, value in meta.items():
                meta_elem = ET.SubElement(ext, f"{{{CAMUNDA_NS}}}meta", key=str(key))
                meta_elem.text = str(value)

        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class ConnectorServiceTask:
    """
        <serviceTask id="ServiceTask_1" name="HTTP Connector Task">
            <extensionElements>
                <camunda:connector>
                    <camunda:connectorId>http-connector</camunda:connectorId>
                    <camunda:inputOutput>
                        <camunda:inputParameter name="url">http://host.docker.internal:8081</camunda:inputParameter>
                        <camunda:inputParameter name="method">POST</camunda:inputParameter>
                        <camunda:inputParameter name="payload">{"name": "approval"}</camunda:inputParameter>
                    </camunda:inputOutput>
                </camunda:connector>
            </extensionElements>
        </serviceTask>
    """
    def __init__(self, process, id, name, config, seq=None, next=None):
        url = None
        method = None
        payload = None
        config = parse_config_meta_next(config)

        if config: 
            url = config.get('url', None)
            method = config.get('method', 'GET')
            payload = config.get('payload', None)

        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=id, name=name)
        ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
        connector = ET.SubElement(ext, f"{{{CAMUNDA_NS}}}connector")
        ET.SubElement(connector, f"{{{CAMUNDA_NS}}}connectorId").text = "http-connector"
        io = ET.SubElement(connector, f"{{{CAMUNDA_NS}}}inputOutput")
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="url").text = url
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="method").text = method
        if payload:
            ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="payload").text = json.dumps(payload)
        
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class ExclusiveGateway:
    """
        <exclusiveGateway id="ExclusiveGateway_1" name="Decision Point" />
    """ 
    def __init__(self, process, id, name=None, seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", id=id, name=name)
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class SequenceFlow:
    def __init__(self, process, id, source_ref, target_ref, condition_expression=None):
        """
            Creates a Sequence Flow element connecting two other elements.
            Args:
                process (Process): The parent process object.
                id (str): The unique ID of the sequence flow.
                source_ref (str): The ID of the source element (e.g., a task or gateway).
                target_ref (str): The ID of the target element.
                condition_expression (str, optional): A JUEL expression for conditional flows, typically used for paths from a gateway (e.g., '${approved == true}').
        """
        attribs = {
            "id": id,
            "sourceRef": source_ref,
            "targetRef": target_ref
        }
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}sequenceFlow", **attribs)
        if condition_expression: # Creates the <conditionExpression> child element for the flow
            condition = ET.SubElement(
                self.element,
                f"{{{BPMN_NS}}}conditionExpression",
                attrib={"xsi:type": "tFormalExpression"}
            )
            condition.text = condition_expression

class CallActivity:
    """
        <callActivity id="call_approval_subprocess" name="Call Reusable Subprocess" calledElement="approval_process">
            <extensionElements>
                <camunda:out source="approved" target="approved" />
                <camunda:out source="rejection_reason" target="rejection_reason" />
                <camunda:in source="rsa" target="rsa" />
            </extensionElements>
        </callActivity>    
    """
    def __init__(self, process, id, name, config=None, meta=None, seq=None, next=None):
        config = parse_config_meta_next(config)
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}callActivity", id=id, name=name, **(config if config else {}))
        meta = parse_config_meta_next(meta)
        if meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for key, value in meta.items():
                # Distinguish between 'in' and 'out' mappings
                if key.startswith('in.'): # eg. in.rsa
                    key = key.split('in.')[-1]
                    ET.SubElement(ext, f"{{{CAMUNDA_NS}}}in", source=key, target=value)
                elif key.startswith('out'):
                    key = key.split('out.')[-1]
                    ET.SubElement(ext, f"{{{CAMUNDA_NS}}}out", source=key, target=value)
                else:
                    raise ValueError(f"Meta key must start with 'in.' or 'out.': {key}")
                
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

class BoundaryEvent:
    """
        <boundaryEvent id="catch_rejection" attachedToRef="call_approval_subprocess">
            <errorEventDefinition errorRef="REJECTION_ERROR" />
        </boundaryEvent>
    """
    def __init__(self, process, id, name, errorRef=None, config=None, meta=None, seq=None, next=None):
        config = parse_config_meta_next(config)
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}boundaryEvent", id=id, name=name, **(config if config else {}))
        if errorRef:    
            ET.SubElement(self.element, f"{{{BPMN_NS}}}errorEventDefinition", errorRef=errorRef)
                
        self.seq = seq
        self.next = parse_config_meta_next(next)
        process._add_element(self.element, id)

def parse_workflows_excel(file_path):
    """
    Parses a multi-sheet Excel file and returns a dictionary of DataFrames.
    Args:
        file_path (str): The path to the Excel file.
    Returns:
        dict: A dictionary where keys are sheet names and values are pandas DataFrames.
              Returns an empty dictionary if the file cannot be read.
    """
    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        dataframes = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in sheet_names}
        return dataframes

    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

def parse_config_meta_next(text):
    """
    Parses a string from an Excel cell.
    The string can be:
        1. A simple integer (for the 'Next' column).
        2. A multi-line YAML formatted string (for 'Config' and 'Meta' columns).
        3. Empty or NaN, which returns None.
    Args:
        text (str): The text from the Excel cell.
    Returns:
        A Python object (int, dict, list, etc.), or None if the text is empty or invalid.
    Raises:
        ValueError: If the text cannot be parsed as an integer or YAML.
    """
    # Return None if the cell is empty
    if not text or pd.isna(text):
        return None
    if isinstance(text, int):
        return text
    if isinstance(text, float) and text.is_integer():
        return int(text)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        print(f"Warning: Could not parse content as YAML. Content: '{text}'\\nError: {e}")
        return None

def get_int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
    
def get_str_or_none(value):
    return None if pd.isna(value) else value

def handle(wf, tElm, df): 
    if tElm.upper() == "ERROR": # maybe we don't really need a separete top elm for errors
        print("Processing Errors...")
        for _, row in df.iterrows(): # multiple error top level elements
            d = dict(row)
            id = get_str_or_none(d.get("Id"))
            name = get_str_or_none(d.get("Name"))
            error_code = id
            error = Error(id=id, name=name, error_code=error_code)
            wf.add_error(error)

    elif tElm.upper() == "PROCESS":
        print("Processing Process...")
        
        proc = Process(id=f"{wf.name}_process", is_executable=True, history_ttl="180")
        wf.add_process(proc)
        
        # handle elements
        flows = {}
        for _, row in df.iterrows(): # multiple elements and flows for one process
            d = dict(row)
            seq = get_int_or_none(d.get("Seq", None))
            bpmnElm = get_str_or_none(d.get("BPMNElm"))
            id = get_str_or_none(d.get("Id"))
            name = get_str_or_none(d.get("Name"))
            next = get_str_or_none(d.get("Next", None))
            config = get_str_or_none(d.get("Config", None)) 
            meta = get_str_or_none(d.get("Meta", None)) 
            errorRef = get_str_or_none(d.get("ErrorRef", None))

            if bpmnElm.upper() == "STARTEVENT":
                flows[seq] = StartEvent(proc, id=id, seq=seq, next=next)
            elif bpmnElm.upper() == "ENDEVENT":
                flows[seq] = EndEvent(proc, id=id, errorRef=errorRef, seq=seq, next=next)
            elif bpmnElm.upper() == "USERTASK":
                flows[seq] = UserTask(proc, id=id, name=name, config=config, meta=meta, seq=seq, next=next)
            elif bpmnElm.upper() == "SERVICETASK":
                flows[seq] = ConnectorServiceTask(proc, id=id, name=name, config=config, seq=seq, next=next)
            elif bpmnElm.upper() == "EXCLUSIVEGATEWAY": 
                flows[seq] = ExclusiveGateway(proc, id=id, name=name, seq=seq, next=next)
            elif bpmnElm.upper() == "CALLACTIVITY":
                flows[seq] = CallActivity(proc, id=id, name=name, config=config, meta=meta, seq=seq, next=next)
            elif bpmnElm.upper() == "BOUNDARYEVENT":
                flows[seq] = BoundaryEvent(proc, id=id, name=name, errorRef=errorRef, config=config, meta=meta, seq=seq, next=next)
            else:
                print(f"Warning: Unknown BPMN Element '{bpmnElm}' for Id '{id}'. Skipping element creation.")
        
        # handle flows after all elements are created
        print(flows)
        for n in sorted(flows.keys()):
            elm = flows[n]
            id = elm.element.get("id")
            next = elm.next
            print("")
            if next: 
                if isinstance(next, int): # default flow
                    SequenceFlow(proc, id=f"Flow_{id}_to_{flows[next].element.get('id')}", source_ref=id, target_ref=flows[next].element.get('id'))
                elif isinstance(next, dict): # conditional flows, eg. {'${approved == true}': '5', '${approved == false}': '6'}
                    for k, v in next.items():
                        target_seq = get_int_or_none(v)
                        target_id = flows[target_seq].element.get("id") if target_seq and target_seq in flows else None
                        if target_id:
                            flow_id = f"Flow_{id}_to_{target_id}"
                            SequenceFlow(proc, id=flow_id, source_ref=id, target_ref=target_id, condition_expression=k)
                        else:
                            print(f"Warning: Target sequence '{v}' not found for condition '{k}' in element id: {id}")
                else:
                    raise ValueError(f"Invalid 'next' value: {next} for element id: {id}")
            else: 
                print(f"No 'next' defined for element id: {id}")

if __name__ == "__main__":
    file_to_parse = 'workflows.xlsx'

    parsed_data = parse_workflows_excel(file_to_parse)
    if parsed_data:
        print(f"Successfully parsed {len(parsed_data)} sheets into a dictionary of dataframes.")
        for name, df in parsed_data.items():
            print(f"\nDataFrame from Sheet '{name}':")
            print(df.head())

            # Generate workflow for each sheet
            print(f"\nGenerating workflow for sheet: {name}")
            wf = Workflow(id=f"{name}_definitions", name=name)
        
            # Iterate each unique top elm
            for tElm in df['TopElm'].unique(): 
                print(f"\nProcessing TopElm: {tElm}")
                handle(wf, tElm, df[df['TopElm'] == tElm])

            # Output the generated BPMN XML
            print(wf.to_pretty_xml())
            wf.to_xml(f"{name}_generated.bpmn") 
