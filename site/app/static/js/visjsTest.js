var nodes = null;
var edges = null;
var network = null;

console.log("Loaded visjsTest.js");

var exampleDRS = "[x2,e1,x4,e3|.NAME(x2),.ENTITY(x4),Jim(x2),like(e3),.MOD(e3,e1,x2),.EVENT(e1),jump(e1),.AGENT(e1,x2),.THEME(e1,x4),over(x4),dog(x4)]";
var exampleDRS2 = "[x5,x1,e2,x4,e3| .ENTITY(x4),.ENTITY(x1),boy(x5),girl(x1),like(e3,x1,e2),eat(e2),.EVENT(e2),.AGENT(e2,x1),.THEME(e2,x4),plums(x4)]";

function destroy() {
  if (network !== null) {
    network.destroy();
    network = null;
  }
}

function draw() {
  destroy();

  document.getElementById("message").innerHTML = '[x2,e1,x4,e3| .NAME(x2),.ENTITY(x4),Jim(x2),like(e3),.MOD(e3,e1,x2),.EVENT(e1),jump(e1),.AGENT(e1,x2),.THEME(e1,x4),over(x4),dog(x4)]';

  // create a network
  var container = document.getElementById('mynetwork');
  var data = parseDRS(exampleDRS);//drsTest();

  var options = {
    physics: { stabilization: false }
  };

  network = new vis.Network(container, data, options);
}

/*
    This function parses a DRS expression and generates nodes and edges
 */
function parseDRS(drs) {

    var variables = drs.split('|')[0].slice(1).split(',');
    var expressions = drs.split('|')[1].split(/,(?![^\(\[]*[\]\)])/);
    console.log("expressions: " + expressions);

    var terminals = expressions.filter(function(item){
        return !(item.startsWith("."))
    });
    console.log("terminals: " + terminals);

    var terminalMap = {};
    terminals.forEach(function(item){
        terminalMap[item.match(/\(([^)]+)\)/)[1]] = item.split('(')[0]
    });
    console.log(terminalMap);

    var names = expressions.filter(function(item){
        return item.startsWith(".NAME")
    });
    console.log("Names: " + names);

    var nameNodes = [];     // Red Nodes

    names.forEach(function(node){
        var nodeId = node.match(/\(([^)]+)\)/)[1]
        nameNodes.push({
            id: nodeId,
            label: "Name: " + terminalMap[nodeId],
            color: 'red',
            shape: 'circle'
        })
    });
    console.log("name nodes: " + String(nameNodes));

    var entities = expressions.filter(function(item){
        return item.startsWith(".ENTITY")
    });
    console.log("entities: " + entities);

    var entityNodes = [];

    entities.forEach(function(node){
        var nodeId = node.match(/\(([^)]+)\)/)[1]
        entityNodes.push({
            id: nodeId,
            label: "Entity: " + terminalMap[nodeId],
            color: 'orange',
            shape: 'circle'
        })
    });
    console.log("entity nodes: " + String(entityNodes));

    var events = expressions.filter(function(item){
        return item.startsWith(".EVENT")
    });
    console.log("events: " + events);

    var eventNodes = [];

    events.forEach(function(node){
        var nodeId = node.match(/\(([^)]+)\)/)[1]
        eventNodes.push({
            id: nodeId,
            label: "Event: " + terminalMap[nodeId],
            color: 'green',
            shape: 'circle'
        })
    });
    console.log("event nodes: " + String(eventNodes));

    /*
        This section is for edges

     */
    var agentEdges = [];
    var agents = expressions.filter(function(item){
        return item.startsWith(".AGENT")
    });
    console.log("agents: " + agents);

    agents.forEach(function(node){
        var from = node.match(/\(([^)]+)\)/)[1].split(',')[0]
        var to = node.match(/\(([^)]+)\)/)[1].split(',')[1]
        agentEdges.push({
            from: from,
            to: to,
            label: "AGENT"
        })
    });
    console.log(agentEdges);

    var modEdges = [];
    var mods = expressions.filter(function(item){
        return item.startsWith(".MOD")
    });
    console.log("mods: " + mods);

    mods.forEach(function(node){
        var mod = node.match(/\(([^)]+)\)/)[1].split(',')[0]
        var from = node.match(/\(([^)]+)\)/)[1].split(',')[1]
        var to = node.match(/\(([^)]+)\)/)[1].split(',')[2]
        modEdges.push({
            from: from,
            to: to,
            label: "MOD: " + terminalMap[mod]
        })
    });
    console.log(modEdges)

    var themeEdges = [];
    var themes = expressions.filter(function(item){
        return item.startsWith(".THEME")
    });
    console.log("themes: " + themes);

    themes.forEach(function(node){
        var from = node.match(/\(([^)]+)\)/)[1].split(',')[0]
        var to = node.match(/\(([^)]+)\)/)[1].split(',')[1]
        themeEdges.push({
            from: from,
            to: to,
            label: "THEME",
        })
    });
    console.log(themeEdges);


    nodes = nameNodes.concat(eventNodes).concat(entityNodes);
    edges = agentEdges.concat(modEdges).concat(themeEdges);

    console.log(nodes);

    return {nodes:nodes, edges:edges};

}
function drsTest(){
// [x2,e1,x4,e3|
// .NAME(x2),.ENTITY(x4),Jim(x2),like(e3),.MOD(e3,e1,x2),.EVENT(e1),jump(e1),.AGENT(e1,x2),.THEME(e1,x4),over(x4),dog(x4)]
    var nameNodes = [];     // Red Nodes
    var entityNodes = [];   // Orange Entities
    var eventNodes = [];    // Green Nodes
    var entityNodes = [];

    var edges = [];     // Black Edges

    nameNodes.push({
        id: 2,
        label: "Name:Jim",
        color: 'red'
    });

    entityNodes.push({
        id: 4,
        label: "Entity:dog",
        color: 'orange'
    });

    eventNodes.push({
        id: 1,
        label: "Event:jump",
        color: 'green'
    });

    edges.push({
        from: 1,
        to: 2,
        label: "MOD:like"
    });

    edges.push({
        from: 1,
        to: 4,
        label: "THEME:over"
    })

    console.log("name nodes: " + String(nameNodes));
    console.log("event nodes: " + eventNodes);
    console.log("entity nodes: " + String(entityNodes));
    nodes = nameNodes.concat(eventNodes).concat(entityNodes);

    console.log("Generated Nodes and Edges");
    console.log(nodes);

    return {nodes:nodes, edges:edges};

}
