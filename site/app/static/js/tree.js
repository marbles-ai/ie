/**
 * Created by tjt7a on 6/28/17.
 *
 * The code was adapted from Microsoft's:
 * http://msrsplatdemo.cloudapp.net/TreeHelpers.js
 */


var font = "'Sorts Mill Goudy'";
var largeSize = "24px";
var smallSize = "13px";
var textheight = 20;
var between = 25;
var lineoffsettop = 8;
var lineoffsetbottom = -2;


// constructor for a treenode object, representing one node in a constituent tree.
function Treenode(label) {
    this.label = label;
    this.children = [];
    this.toString = function() {
        if (this.children.length == 0) {
            return this.label;
        }
        var pieces = ["(" + this.label];
        for (var i = 0; i < this.children.length; ++i) {
            pieces.push(" " + this.children[i].toString());
        }
        pieces.push(")");
        return pieces.join("");
    }
}

function parseCnfTreeHelper(str, pos, maxpos) {
    //log("parsing at position " + pos.index + ": " + str.substr(pos.index));
    // skip past any initial whitespace.
    while (str.charAt(pos.index) == ' ') pos.inc();

    if (str.charAt(pos.index) == '(') {
        var labelstart = pos.inc();
        while (str.charAt(pos.index) != ' ') pos.inc();
        var n = new Treenode(str.substr(labelstart, pos.index - labelstart));
        while (true) {
            while (str.charAt(pos.index) == ' ') pos.inc();
            if (str.charAt(pos.index) == ')') {
                pos.inc();
                break;
            }
            var child = parseCnfTreeHelper(str, pos);
            //log("add child " + n.label + " ===/ " + child.label);
            n.children.push(child);
        }
        return n;
    }

    var st = pos.index;
    while (str.charAt(pos.index) != ' ' && str.charAt(pos.index) != ')') pos.inc();
    return new Treenode(str.substr(st, pos.index - st));
}

// parse a CNF-style tree representation into a tree of nodes.
function parseCnfTree(str) {
    return parseCnfTreeHelper(str, new PositionRef(str.length));
}

function drawConstituentTree(canvas, ctx, pt) {
    var p = new PositionRef(1000000);
    ctx.font = largeSize + " " + font;
    layoutTree(pt, ctx, p);
    layoutTreeFixLayer(pt);
    layoutTreeFixMid(pt);
    lastTree = pt;

    var computedHeight = textheight + pt.layer * (textheight + between);
    canvas.width = (p.index + 10) * 1;
    canvas.height = (computedHeight + 10) * 1;

    ctx.font = largeSize + " " + font;
    drawTree(pt, ctx, pt.layer);
}

function drawTree(pt, ctx, toplayer) {
    ctx.textAlign = "center";
    var y = bottomY(pt.layer, toplayer);

    ctx.fillText(pt.label, pt.mid, y);
    y += lineoffsettop;

    for (var x in pt.children) {
        var color = "#b0b0b0";
        if (pt.children[x].label.indexOf('*') != -1)
            color = "red";
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(pt.mid, y);
        ctx.lineTo(pt.children[x].mid, topY(pt.children[x].layer, toplayer) + lineoffsetbottom);
        ctx.stroke();
        drawTree(pt.children[x], ctx, toplayer);
    }
}
