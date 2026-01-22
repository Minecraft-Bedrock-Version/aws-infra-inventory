import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from collectors.collector_handler import handler as run_collectors
from normalizers.normalizer_handler import run_normalizers
from graph_builder.graph_handler import GraphAssembler

def lambda_handler(event, context):

    raw_data = run_collectors(event, context)

    normalized_data = run_normalizers(raw_data)

    assembler = GraphAssembler()
    graph = assembler.assemble([normalized_data])
    
    ??? = run_??(graph)

    return ??
