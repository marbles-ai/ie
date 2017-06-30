/**
 * Created by tjt7a on 6/28/17.
 *
 * The code was adapted from Microsoft's:
 * http://msrsplatdemo.cloudapp.net/TreeHelpers.js
 */


/*
    Example javascript request:
 http://msrsplat.cloudapp.net/SplatServiceJson.svc
 /Analyze?language=en
 &analyzers=Constituency_Tree-PennTreebank3-SplitMerge
 &appId=89839f78-e146-48c6-8e55-96de0b30057a
 &input=I%20like%20apples!

    Result:
 [{"Key": "Constituency_Tree-PennTreebank3-SplitMerge", "Value": ["(TOP (S (NP (PRP I)) (VP (VBP like) (NNS apples)) (. !)))"]}]
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

// constructor for a position reference object.  passes a position by reference,
// and checks for access beyond bounds
function PositionRef(max) {
    this.index = 0;
    this.maxpos = max;
    this.inc = function() {
        if (++this.index > this.maxpos)
            throw new exception("access beyond end of array");
        return this.index;
    }
    this.add = function(i) {
        this.index += i;
        if (this.index > this.maxpos)
            throw new exception("access beyond end of array");
        return this.index;
    }
}

function parseCnfTreeHelper(str, pos, maxpos) {
    // skip past any initial whitespace.
    while (str.charAt(pos.index) == ' ') pos.inc();

    // Start a label with '('
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


function distributeExtraWeight(n, extra) {
    n.right += extra;
    var kids = n.children.length;
    if (kids == 0) {
        return;
    }
    if (kids == 1) {
        distributeExtraWeight(n.children[0], extra);
        return;
    }
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

function layoutTree(n, ctx, pos) {
    n.left = pos.index;
    if (n.children.length == 0) {
        n.layer = 0;
        pos.add(ctx.measureText(n.label).width);
        pos.add(10);
        n.right = pos.index;
        return;
    }

    n.layer = 1;
    var totalWidth = 0;
    for (x in n.children) {
        var child = n.children[x];
        layoutTree(child, ctx, pos);
        if (child.layer >= n.layer) {
            n.layer = child.layer + 1;
        }
        totalWidth += child.right - child.left;
    }
    var mywidth = ctx.measureText(n.label).width + 10;
    if (mywidth > totalWidth) {
        var extra = mywidth - totalWidth;
        pos.add(extra);
        distributeExtraWeight(n, extra);
    }
    n.right = pos.index;
}
function layoutTreeFixLayer(n) {
    for (x in n.children) {
        var child = n.children[x];
        if (child.layer > 0 && child.layer < n.layer - 1) {
            child.layer = n.layer - 1
        }
        layoutTreeFixLayer(child);
    }
}
function layoutTreeFixMid(n) {
    if (n.children.length == 0)
    {
        n.mid = Math.round((n.left + n.right) / 2);
        return;
    }
    var sum = 0;
    var denom = 0;
    for (x in n.children) {
        var child = n.children[x];
        layoutTreeFixMid(child);
        var weight = 1 / (1 + child.layer);
        denom += weight;
        sum += child.mid * weight;
    }
    n.mid = Math.round(sum / denom);
}

function topY(layer, toplayer) {
    var l = toplayer - layer;
    return l * (textheight + between);
}

function bottomY(layer, toplayer) {
    var l = toplayer - layer;
    return textheight + l * (textheight + between);
}

function drawTree(pt, ctx, toplayer) {
    ctx.textAlign = "center";
    var y = bottomY(pt.layer, toplayer);

    ctx.fillText(pt.label, pt.mid, y);
    y += lineoffsettop;

    for (var x in pt.children) {
        var color = "blue";
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
