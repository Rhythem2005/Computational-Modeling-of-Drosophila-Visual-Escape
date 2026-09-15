import os
import sys
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from neuprint import Client, fetch_custom

def main():
    # Load environment variables
    load_dotenv()
    
    server = os.getenv('NEUPRINT_SERVER', 'neuprint.janelia.org')
    token = os.getenv('NEUPRINT_TOKEN')
    dataset = os.getenv('NEUPRINT_DATASET', 'manc:v1.0') # Defaulting to manc:v1.0 which is Male Adult Nerve Cord
    
    if not token:
        print("Error: NEUPRINT_TOKEN environment variable not set.")
        print("Please create a .env file or set the environment variable with your neuPrint auth token.")
        print("Example .env file content:")
        print("NEUPRINT_SERVER=neuprint.janelia.org")
        print("NEUPRINT_TOKEN=your_token")
        sys.exit(1)
        
    print(f"Connecting to {server} for dataset {dataset}...")
    try:
        client = Client(server, dataset=dataset, token=token)
    except Exception as e:
        print(f"Failed to connect to neuPrint: {e}")
        sys.exit(1)
        
    print("Connection successful!\n")
    
    # 1. Verify existence of neuron classes
    target_classes = ['LPLC2', 'LC4', 'DNp06']
    verification_results = {}
    
    # Using cypher to check if these types exist in the dataset
    print("Verifying neuron classes...")
    for n_type in target_classes:
        query = f"""
        MATCH (n:Neuron)
        WHERE n.type = '{n_type}'
        RETURN count(n) as count
        """
        try:
            res = fetch_custom(query, client=client)
            count = res['count'].iloc[0]
            if count > 0:
                verification_results[n_type] = "FOUND"
                print(f"{n_type}: FOUND ({count} instances)")
            else:
                verification_results[n_type] = "NOT FOUND"
                print(f"{n_type}: NOT FOUND")
        except Exception as e:
            verification_results[n_type] = f"ERROR: {e}"
            print(f"{n_type}: ERROR - {e}")
            
    print("\nVerifying connections...")
    connections = [('LPLC2', 'DNp06'), ('LC4', 'DNp06')]
    verified_edges = []
    
    for pre, post in connections:
        # Check if they connect
        query = f"""
        MATCH (pre:Neuron)-[w:ConnectsTo]->(post:Neuron)
        WHERE pre.type = '{pre}' AND post.type = '{post}'
        RETURN pre.type as pre_type, post.type as post_type, sum(w.weight) as total_weight
        """
        try:
            res = fetch_custom(query, client=client)
            if len(res) > 0 and res['total_weight'].iloc[0] > 0:
                print(f"{pre} -> {post}: VERIFIED (Total weight: {res['total_weight'].iloc[0]})")
                verified_edges.append({'pre': pre, 'post': post, 'weight': res['total_weight'].iloc[0]})
            else:
                print(f"{pre} -> {post}: NOT FOUND")
        except Exception as e:
            print(f"{pre} -> {post}: ERROR - {e}")
            
    # Save CSV
    if verified_edges:
        df = pd.DataFrame(verified_edges)
        csv_path = '../data/verified_connections.csv'
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        print(f"\nSaved connectivity data to {csv_path}")
        
        # Generate Graph
        G = nx.DiGraph()
        for edge in verified_edges:
            G.add_edge(edge['pre'], edge['post'], weight=edge['weight'])
            
        plt.figure(figsize=(6, 4))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=10, font_weight='bold', arrows=True)
        
        # Draw edge labels
        edge_labels = {(u, v): d['weight'] for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        
        plt.title('Verified Circuit Connectivity')
        graph_path = '../graphs/circuit_graph.png'
        os.makedirs(os.path.dirname(graph_path), exist_ok=True)
        plt.savefig(graph_path)
        print(f"Saved graph visualization to {graph_path}")
    else:
        print("\nNo verified connections found. CSV and Graph were not generated.")

if __name__ == "__main__":
    main()
