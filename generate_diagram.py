import xml.etree.ElementTree as ET

def generate_bpmn_diagram(file_path):
    """
    Reads a BPMN file, generates a simple BPMNDiagram for it, and updates the file.

    Args:
        file_path: The path to the BPMN file.
    """
    try:
        # Register namespaces to avoid long prefixes in the output
        ET.register_namespace('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI')
        ET.register_namespace('omgdc', 'http://www.omg.org/spec/DD/20100524/DC')
        ET.register_namespace('omgdi', 'http://www.omg.org/spec/DD/20100524/DI')

        tree = ET.parse(file_path)
        root = tree.getroot()

        namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
            'omgdi': 'http://www.omg.org/spec/DD/20100524/DI'
        }

        process = root.find('bpmn:process', namespaces)
        if process is None:
            print("Error: No <process> element found in the BPMN file.")
            return

        # Check if a diagram already exists
        if root.find('bpmndi:BPMNDiagram', namespaces) is not None:
            print("Diagram already exists. Aborting.")
            return

        # --- Create the diagram structure ---
        bpmn_diagram = ET.Element('bpmndi:BPMNDiagram', id='BPMNDiagram_1')
        bpmn_plane = ET.Element('bpmndi:BPMNPlane', id='BPMNPlane_1', bpmnElement=process.get('id'))
        bpmn_diagram.append(bpmn_plane)

        elements = {}
        # --- Layout and create shapes for process elements ---
        x_pos = 150
        y_pos = 100
        for element in process:
            elem_id = element.get('id')
            if 'Event' in element.tag:
                width, height = 36, 36
            elif 'Task' in element.tag:
                width, height = 100, 80
            elif 'Gateway' in element.tag:
                width, height = 50, 50
            else:
                continue # Skip sequence flows for now

            bounds = ET.Element('omgdc:Bounds', height=str(height), width=str(width), x=str(x_pos), y=str(y_pos))
            shape = ET.Element('bpmndi:BPMNShape', id=f'{elem_id}_di', bpmnElement=elem_id)
            shape.append(bounds)
            bpmn_plane.append(shape)
            
            elements[elem_id] = {'x': x_pos, 'y': y_pos, 'width': width, 'height': height}
            x_pos += width + 100 # Move to the right for the next element

        # --- Create edges for sequence flows ---
        for flow in process.findall('bpmn:sequenceFlow', namespaces):
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            source_elem = elements.get(source_ref)
            target_elem = elements.get(target_ref)

            if source_elem and target_elem:
                edge = ET.Element('bpmndi:BPMNEdge', id=f'{flow_id}_di', bpmnElement=flow_id)
                
                # Waypoint from source to target
                waypoint1 = ET.Element('omgdi:waypoint', x=str(source_elem['x'] + source_elem['width']), y=str(source_elem['y'] + source_elem['height'] // 2))
                waypoint2 = ET.Element('omgdi:waypoint', x=str(target_elem['x']), y=str(target_elem['y'] + target_elem['height'] // 2))
                
                edge.append(waypoint1)
                edge.append(waypoint2)
                bpmn_plane.append(edge)

        root.append(bpmn_diagram)

        # Write the updated XML back to the file
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"Successfully generated and added BPMN diagram to {file_path}")

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Main execution ---
if __name__ == "__main__":
    bpmn_file = "workflow.bpmn"
    generate_bpmn_diagram(bpmn_file)
