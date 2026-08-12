MERGE (s:Satellite {id: 'SAT-001'})
MERGE (power:Component {id: 'POWER-001', type: 'power'})
MERGE (thermal:Component {id: 'THERMAL-001', type: 'thermal'})
MERGE (s)-[:CONTAINS]->(power)
MERGE (s)-[:CONTAINS]->(thermal)
MERGE (thermal)-[:DEPENDS_ON]->(power);
