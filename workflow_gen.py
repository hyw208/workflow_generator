import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import pandas as pd

# --- XML Namespace Configuration ---
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"

ET.register_namespace('', BPMN_NS)
ET.register_namespace('camunda', CAMUNDA_NS)
# BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
# OMGDC_NS = "http://www.omg.org/spec/DD/20100524/DC"
# OMGDI_NS = "http://www.omg.org/spec/DD/20100524/DI"
# ET.register_namespace('bpmndi', BPMNDI_NS)
# ET.register_namespace('omgdc', OMGDC_NS)
# ET.register_namespace('omgdi', OMGDI_NS)      

class Workflow:
    def __init__(self, id="Definitions_1", name=None, target_namespace="http://bpmn.io/schema/bpmn"):
        self.name = name
        self.root = ET.Element(f"{{{BPMN_NS}}}definitions", targetNamespace=target_namespace, id=id,
                               xmlns_xsi="http://www.w3.org/2001/XMLSchema-instance",
                               xmlns_bpmndi="http://www.omg.org/spec/BPMN/20100524/DI",
                               xmlns_omgdc="http://www.omg.org/spec/DD/20100524/DC",
                               xmlns_omgdi="http://www.omg.org/spec/DD/20100524/DI")
        self.process = None
        self.error = None

    def add_error(self, error):
        self.error = error
        self.root.append(error.element)

    def add_process(self, process):
        self.process = process
        self.root.append(process.element)

    def to_pretty_xml(self):
        self._indent(self.root)
        rough_string = ET.tostring(self.root, 'utf-8', xml_declaration=True)
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def to_xml(self, filename):
        # self._generate_diagram()
        tree = ET.ElementTree(self.root)
        self._indent(self.root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def _indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            for child in elem:
                self._indent(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

"""     def _generate_diagram(self):
        diagram = ET.SubElement(self.root, f"{{{BPMNDI_NS}}}BPMNDiagram", id="BPMNDiagram_1")
        plane = ET.SubElement(diagram, f"{{{BPMNDI_NS}}}BPMNPlane", id="BPMNPlane_1", bpmnElement=self.process.id)

        # Generate shapes
        for elem_id, info in self.process.positions.items():
            shape = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", id=f"{elem_id}_di", bpmnElement=elem_id)
            bounds = ET.SubElement(shape, f"{{{OMGDC_NS}}}Bounds", **info['coords'])

        # Generate edges
        for flow in self.process.element.findall(f'{{{BPMN_NS}}}sequenceFlow'):
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            source_info = self.process.positions.get(source_ref)
            target_info = self.process.positions.get(target_ref)

            if source_info and target_info:
                edge = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNEdge", id=f"{flow_id}_di", bpmnElement=flow_id)
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=str(int(source_info['coords']['x']) + int(source_info['coords']['width'])), y=str(int(source_info['coords']['y']) + int(source_info['coords']['height']) // 2))
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=target_info['coords']['x'], y=str(int(target_info['coords']['y']) + int(target_info['coords']['height']) // 2))
 """

class Error:
    def __init__(self, id, name, error_code):
        attribs = {"id": id, "name": name, "errorCode": error_code}
        self.element = ET.Element(f"{{{BPMN_NS}}}error", attrib=attribs)

class Process:
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        self.id = id
        self.element = ET.Element(
            f"{{{BPMN_NS}}}process",
            id=id,
            isExecutable=str(is_executable).lower(),
            **{f"{{{CAMUNDA_NS}}}historyTimeToLive": history_ttl}
        )
        self.elements = {}
        self.positions = {}
        self._x_pos = 150
        self._y_pos = 100

    def _add_element(self, element, elem_id, width, height):
        self.elements[elem_id] = element
        self.positions[elem_id] = {
            'coords': {'x': str(self._x_pos), 'y': str(self._y_pos), 'width': str(width), 'height': str(height)}
        }
        self._x_pos += width + 100

    def add_sequence_flow(self, id, source_ref, target_ref):
        return ET.SubElement(self.element, f"{{{BPMN_NS}}}sequenceFlow", id=id, sourceRef=source_ref, targetRef=target_ref)

class StartEvent:
    def __init__(self, process, id="StartEvent_1", seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}startEvent", id=id)
        self.seq = seq
        self.next = parse_config_meta_next(next, d2=':')
        process._add_element(self.element, id, 36, 36)

class EndEvent:
    def __init__(self, process, id="EndEvent_1", errorRef=None, seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}endEvent", id=id)
        if errorRef:    
            ET.SubElement(self.element, f"{{{BPMN_NS}}}errorEventDefinition", errorRef=errorRef)
        self.seq = seq
        self.next = parse_config_meta_next(next, d2=':')
        process._add_element(self.element, id, 36, 36)

class UserTask:
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
        self.next = parse_config_meta_next(next, d2=':')
        process._add_element(self.element, id, 100, 80)

class ConnectorServiceTask:
    def __init__(self, process, id, name, config, seq=None, next=None):
        url = None
        method = None
        payload = None
        config = parse_config_meta_next(config)

        if config: 
            url = config.get('url', None)
            method = config.get('method', 'GET')
            payload = config.get('payload', None)
            if payload:
                payload = json.loads(payload)

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
        self.next = parse_config_meta_next(next, d2=':')
        process._add_element(self.element, id, 100, 80)

class ExclusiveGateway:
    def __init__(self, process, id, name=None, seq=None, next=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", id=id, name=name)
        self.seq = seq
        self.next = parse_config_meta_next(next, d2=':')
        process._add_element(self.element, id, 50, 50)

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

def parse_config_meta_next(text, d2='='):
    """
        line delimiter is comma
        whereas key-value delimiter is defaulted to '=' 
        e.g. config and meta using '='
            url=http://host.docker.internal:8081, 
            method=POST, 
            payload={"name": "approval"}
        eg. next using ':'
            ${approved == true}: 5,
            ${approved == false}: 6

            or 

            2
    """
    obj = None
    if text:
        try:
            obj = int(text)
        except ValueError:
            print("Not an integer string")
            obj = {}
            for part in text.split(','):
                if part: 
                    key, value = part.split(d2)
                    obj[key.strip()] = value.strip()
    return obj # None, int, or dict

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

            # Generate workflow for approval tab
            if name == "approval":
                wf = Workflow(id=f"{name}_definitions", name=name)
            
                topElms = df['TopElm'].unique()
                for tElm in topElms: # iterate each unique top elm
                    print(f"\nProcessing TopElm: {tElm}")
                    sub_df = df[df['TopElm'] == tElm]
                    handle(wf, tElm, sub_df)

                wf.to_xml(f"{name}_generated.bpmn") 
