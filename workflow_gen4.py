import xml.etree.ElementTree as ET
import json
import pandas as pd

# --- XML Namespace Configuration ---
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

# --- Main Workflow Class ---
class Workflow:
    def __init__(self, id="Definitions_1", target_namespace="http://bpmn.io/schema/bpmn"):
        self.root = ET.Element(f"{{{BPMN_NS}}}definitions", id=id, targetNamespace=target_namespace)
        self.process = None

    def add_process(self, process):
        self.process = process
        self.root.append(process.element)

    def add_toplevel_element(self, element):
        self.root.append(element)

    def to_xml(self, filename):
        if self.process:
            self._generate_diagram()
        tree = ET.ElementTree(self.root)
        self._indent(self.root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def _generate_diagram(self):
        diagram = ET.SubElement(self.root, f"{{{BPMNDI_NS}}}BPMNDiagram", id="BPMNDiagram_1")
        plane = ET.SubElement(diagram, f"{{{BPMNDI_NS}}}BPMNPlane", id="BPMNPlane_1", bpmnElement=self.process.id)

        for elem_id, info in self.process.positions.items():
            shape = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", id=f"{elem_id}_di", bpmnElement=str(elem_id))
            ET.SubElement(shape, f"{{{OMGDC_NS}}}Bounds", **info['coords'])

        for flow in self.process.element.findall(f'{{{BPMN_NS}}}sequenceFlow'):
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            source_info = self.process.positions.get(source_ref)
            target_info = self.process.positions.get(target_ref)

            if source_info and target_info:
                edge = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNEdge", id=f"{flow_id}_di", bpmnElement=str(flow_id))
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=str(int(float(source_info['coords']['x'])) + int(float(source_info['coords']['width']))), y=str(int(float(source_info['coords']['y'])) + int(float(source_info['coords']['height']) // 2)))
                ET.SubElement(edge, f"{{{OMGDI_NS}}}waypoint", x=str(target_info['coords']['x']), y=str(int(float(target_info['coords']['y'])) + int(float(target_info['coords']['height']) // 2)))

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

# --- BPMN Element Classes ---
class Process:
    def __init__(self, id="Process_1", is_executable=True, history_ttl="180"):
        self.id = id
        self.element = ET.Element(
            f"{{{BPMN_NS}}}process",
            id=str(id),
            isExecutable=str(is_executable).lower(),
            # Do not use double curly braces for keyword arguments
            **{f"{{{CAMUNDA_NS}}}historyTimeToLive": str(history_ttl)}
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

    def add_sequence_flow(self, id, source_ref, target_ref, condition=None):
        flow = ET.SubElement(self.element, f"{{{BPMN_NS}}}sequenceFlow", id=str(id), sourceRef=str(source_ref), targetRef=str(target_ref))
        if condition and str(condition) != 'nan':
            cond_expr = ET.SubElement(flow, f"{{{BPMN_NS}}}conditionExpression", {{f"{{{XSI_NS}}}type": "tFormalExpression"}})
            cond_expr.text = str(condition)
        return flow

class Error:
    def __init__(self, id, name, error_code):
        self.element = ET.Element(f"{{{BPMN_NS}}}error", id=str(id), name=str(name), errorCode=str(error_code))

class StartEvent:
    def __init__(self, process, id, name=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}startEvent", id=str(id), name=str(name) if name and str(name) != 'nan' else str(id))
        process._add_element(self.element, id, 36, 36)

class EndEvent:
    def __init__(self, process, id, name=None, error_ref=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}endEvent", id=str(id), name=str(name) if name and str(name) != 'nan' else str(id))
        if error_ref and str(error_ref) != 'nan':
            ET.SubElement(self.element, f"{{{BPMN_NS}}}errorEventDefinition", errorRef=str(error_ref))
        process._add_element(self.element, id, 36, 36)

class HumanTask:
    def __init__(self, process, id, name, meta=None, extension_meta=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}userTask", id=str(id), name=str(name), **(meta if meta else {{}}))
        if extension_meta:
            ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
            for k, v in extension_meta.items():
                ET.SubElement(ext, f"{{{CAMUNDA_NS}}}meta", key=str(k)).text = str(v)
        process._add_element(self.element, id, 100, 80)

class ConnectorServiceTask:
    def __init__(self, process, id, name, url, method="GET", payload=None):
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}serviceTask", id=str(id), name=str(name))
        ext = ET.SubElement(self.element, f"{{{BPMN_NS}}}extensionElements")
        connector = ET.SubElement(ext, f"{{{CAMUNDA_NS}}}connector")
        ET.SubElement(connector, f"{{{CAMUNDA_NS}}}connectorId").text = "http-connector"
        io = ET.SubElement(connector, f"{{{CAMUNDA_NS}}}inputOutput")
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="url").text = str(url)
        ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="method").text = str(method)
        if payload and str(payload) != 'nan':
            ET.SubElement(io, f"{{{CAMUNDA_NS}}}inputParameter", name="payload").text = str(payload)
        process._add_element(self.element, id, 100, 80)

class ExclusiveGateway:
    def __init__(self, process, id, name=None):
        attribs = {"id": str(id)}
        if name and str(name) != 'nan': attribs["name"] = str(name)
        self.element = ET.SubElement(process.element, f"{{{BPMN_NS}}}exclusiveGateway", **attribs)
        process._add_element(self.element, id, 50, 50)

def parse_workflows_excel(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        return {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

if __name__ == "__main__":
    file_to_parse = 'workflows.xlsx'
    parsed_data = parse_workflows_excel(file_to_parse)

    if "approval" not in parsed_data:
        raise ValueError("No 'approval' sheet found in the Excel file.")

    approval_data = parsed_data["approval"]

    wf = Workflow()
    proc = Process(id="approval_subprocess")
    wf.add_process(proc)

    # Create all elements first
    for index, row in approval_data.iterrows():
        elem_type = str(row.get("BPMNElm", ""))
        elem_id = str(row.get("Seq", ""))
        elem_name = str(row.get("TaskName", ""))
        
        if elem_type == "ERROR":
            error = Error(id=elem_id, name=elem_name, error_code=elem_id)
            wf.add_toplevel_element(error.element)
        elif elem_type == "START":
            StartEvent(proc, id=elem_id, name=elem_name)
        elif elem_type == "USERTASK":
            extension_meta = {}
            if 'Desc' in row and str(row['Desc']) != 'nan':
                try:
                    extension_meta = json.loads(row['Desc'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse extension_meta for {elem_id}: {row['Desc']}")
            HumanTask(proc, id=elem_id, name=elem_name, extension_meta=extension_meta)
        elif elem_type == "SERVICETASK":
            ConnectorServiceTask(proc, id=elem_id, name=elem_name, url=row.get("Desc"), method=row.get("Role"), payload=row.get("Condition"))
        elif elem_type == "EXCLUSIVEGATEWAY":
            ExclusiveGateway(proc, id=elem_id, name=elem_name)
        elif elem_type == "ENDEVENT":
            EndEvent(proc, id=elem_id, name=elem_name, error_ref=row.get("Condition"))

    # Create sequence flows
    flow_counter = 1
    for index, row in approval_data.iterrows():
        source_id = str(row.get("Seq", ""))
        next_steps = str(row.get("NextStep", ""))
        if next_steps and next_steps != 'nan':
            targets = next_steps.split(',')
            for target_id in targets:
                target_id = target_id.strip()
                
                condition = None
                if str(row.get("BPMNElm")) == "EXCLUSIVEGATEWAY":
                    target_row = approval_data[approval_data['Seq'] == target_id]
                    if not target_row.empty:
                        condition = target_row.iloc[0].get('Condition')

                proc.add_sequence_flow(f"Flow_{flow_counter}", source_id, target_id, condition=condition)
                flow_counter += 1

    wf.to_xml("approval_generated.bpmn")
    print("Generated BPMN file: approval_generated.bpmn")
