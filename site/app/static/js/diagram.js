/*
    The purpose of this diagram class is to draw the chord diagram showing
    the relationships between marbles and sources

    This code is based on Nadieh Bremer's:
    http://bl.ocks.org/nbremer/f9dacd23eece9d23669c
*/

var displayWidth = $(window).innerWidth();
var mobileWidth = (displayWidth > 500 ? false : true);

var margin = {top: 10,
              bottom: 10,
              right: 10,
              left: 10};

var width = Math.min(displayWidth, 800) - margin.left - margin.right;

var height = (mobileWidth ? 300 : Math.min(displayWidth, 800)*(5/6)) - margin.top - margin.bottom;

var svg = d3.select("#chart").append("svg")
        .attr("width", (width + margin.left + margin.right))
        .attr("height", (height + margin.top + margin.bottom));

var wrapper = svg.append("g").attr("class", "chordWrapper")
                             .attr("transform", "translate(" +
                                (width / 2 + margin.left) +
                                "," +
                                (height / 2 + margin.top) +
                                ")");;

var outerRadius = Math.min(width, height) / 2 - (mobileWidth ? 80 : 100);

var innerRadius = outerRadius * 0.95;

var opacityDefault = 0.7;

var opacityLow = 0.02;

var pullOutSize = (mobileWidth ? 20 : 50);

// Titles
var titleWrapper = svg.append("g").attr("class", "chordTitleWrapper");
var titleOffset = mobileWidth ? 15 : 40;
var titleSeparate = mobileWidth ? 30 : 0;

// Title in the top-left
titleWrapper.append("text")
    .attr("class", "title left")
    .style("font-size", mobileWidth ? "12px" : "16px")
    .attr("x", (width / 2 + margin.left - outerRadius - titleSeparate))
    .attr("y", titleOffset)
    .text("First Class");

titleWrapper.append("line")
    .attr("class", "titleLine left")
    .attr("x1", (width / 2 + margin.left - outerRadius - titleSeparate) * 0.6)
    .attr("x2", (width / 2 + margin.left - outerRadius - titleSeparate) * 1.4)
    .attr("y1", titleOffset + 8)
    .attr("y2", titleOffset + 8);

titleWrapper.append("text")
    .attr("class", "right right")
    .style("font-size", mobileWidth ? "12px" : "16px")
    .attr("x", (width / 2 + margin.left + outerRadius + titleSeparate))
    .attr("y", titleOffset)
    .text("Second Class");

titleWrapper.append("line")
    .attr("class", "titleLine right")
    .attr("x1", (width / 2 + margin.left - outerRadius - titleSeparate) * 0.6 +
                (outerRadius + titleSeparate) * 2.0)
    .attr("x2", (width / 2 + margin.left - outerRadius - titleSeparate) * 1.4 +
                (outerRadius + titleSeparate) * 2.0)
    .attr("y1", titleSeparate + 8)
    .attr("y2", titleSeparate + 8);

// Animations
var defs = wrapper.append("defs");

var linearGradient = defs.append("linearGradient")
    .attr("id", "animatedGradient")
    .attr("x1", "0%")
    .attr("y1", "0%")
    .attr("x2", "100%")
    .attr("y2", "0")
    .attr("spreadMethod", "reflect");

linearGradient.append("animate")
    .attr("attributeName", "x1")
    .attr("values", "0%;100%")
    .attr("dur", "7s")
    .attr("repeatCount", "indefinite");

linearGradient.append("animate")
    .attr("attributeName", "x2")
    .attr("values", "100%;200%")
    .attr("dur", "7s")
    .attr("repeatCount", "indefinite")

linearGradient.append("stop")
    .attr("offset", "5%")
    .attr("stop-color", "#E8E8E8");


linearGradient.append("stop")
    .attr("offset", "45%")
    .attr("stop-color", "#A3A3A3");
linearGradient.append("stop")
    .attr("offset", "55%")
    .attr("stop-color", "#A3A3A3");

linearGradient.append("stop")
    .attr("offset", "95%")
    .attr("stop-color", "#E8E8E8");

// Data
var Names = [ // Class 1
             "Marble 1 (Macron)",
             "Marble 2 (LePen)",
             "Marble 3 (Trump)",
             "Marble 4 (Health Care)",
             "Marble 5 (Climate Change)",
             "Marble 6 (Bill Nye)",
             "Marble 7 (Apple)",
             "Marble 8 (Patriarchy)",
             "Marble 9 (Chem Trails)",
            "Marble 10 (Russia)",
            "Marble 11 (Syria)",
            "Marble 12 (orange juice)",
            "Other",
            // Class 2
            "",
            "New York Times",
            "CNN",
            "Fox News",
            "Breitbart",
            "Speigel",
            "BBC",
            "The Onion",
            ""
            ];

var respondents = 17533; // The number that make up the whole group

var emptyPerc = 0.5; // What percentage of the circle is empty

var emptyStroke = Math.round(respondents * emptyPerc);

var matrix = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,232,65,44,57,39,123,1373,0], //Administratief personeel
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0,0,11,0,0,24,0], //Ambachtslieden
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,173,43,52,55,36,125,2413,0], //Bedrijfsbeheer (vak)specialisten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,16,13,23,10,37,54,0], //Elementaire beroepen
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,161,24,17,0,2089,85,60,0], //Gezondheidszorg (vak)specialisten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,510,0,0,57,0,0,251,0], //IT (vak)specialisten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,118,10,454,99,1537,271,0], //Juridisch en culturele (vak)specialisten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,21,10,15,125,41,261,0], //Leidinggevende functies
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,2206,37,292,32,116,76,0], //Onderwijsgevenden
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,96,74,43,116,51,135,752,0], //Verkopers en verleners persoonlijke diensten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,34,0,22,27,156,36,0], //Verzorgend personeel
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,1141,0,111,291,0,0,48,0], //Wetenschap en techniek (vak)specialisten
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0,39,0,0,20,109,0], //Other
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,emptyStroke], //dummyBottom
    [232,32,173,32,161,510,16,76,32,96,15,1141,36,0,0,0,0,0,0,0,0,0], //Techniek
    [65,0,43,16,24,0,118,21,2206,74,34,0,0,0,0,0,0,0,0,0,0,0], //Onderwijs
    [44,0,52,13,17,0,10,10,37,43,0,111,39,0,0,0,0,0,0,0,0,0], //Landbouw
    [57,11,55,23,0,57,454,15,292,116,22,291,0,0,0,0,0,0,0,0,0,0], //Kunst, Taal en Cultuur
    [39,0,36,10,2089,0,99,125,32,51,27,0,0,0,0,0,0,0,0,0,0,0], //Gezondheidszorg
    [123,0,125,37,85,0,1537,41,116,135,156,0,20,0,0,0,0,0,0,0,0,0], //Gedrag & Maatschappij
    [1373,24,2413,54,60,251,271,261,76,752,36,48,109,0,0,0,0,0,0,0,0,0], //Economie
    [0,0,0,0,0,0,0,0,0,0,0,0,0,emptyStroke,0,0,0,0,0,0,0,0] //dummyTop
];

var offset = (2 * Math.PI) * (emptyStroke / (respondents + emptyStroke)) / 4;

var chord = newChordLayout()
    .padding(0.02)
    .sortChord(d3.descending)
    .matrix(matrix);

var arc = d3.svg.arc()
    .innerRadius(innerRadius)
    .outerRadius(outerRadius)
    .startAngle(startAngle)
    .endAngle(endAngle);

var path = stretchedChord()
    .radius(innerRadius)
    .startAngle(startAngle)
    .endAngle(endAngle)
    .pullOutSize(pullOutSize);

// Drawing Outer Arcs
var g = wrapper.selectAll("g.group")
    .data(chord.groups)
    .enter().append("g")
    .attr("class", "group")
    .on("mousover", fade(opacityLow))
    .on("mouseout", fade(opacityDefault));

g.append("path")
    .style("stroke", function(d, i){
        return (Names[i] === "" ? "none" : "#00A1DE");
    })
    .style("fill", function(d, i){
        return (Names[i] === "" ? "none" : "auto");
    })
    .attr("d", arc)
    .attr("transform", function(d, i){
        d.pullOutSize = pullOutSize * (d.startAngle + 0.001 > Math.PI ? -1 : 1);
        return "translate(" + d.pullOutSize + ',' + 0 + ")";
    });

// Append Names
g.append("text")
    .each(function(d){
        d.angle = ((d.startAngle + d.endAngle) / 2) + offset;
    })
    .attr("dy", ".35em")
    .attr("class", "titles")
    .style("font-size", mobileWidth ? "8px" : "10px")
    .attr("text-anchor", function(d){
        return d.angle > Math.PI ? "end" : null;
    })
    .attr("transform", function(d, i){
        var c = arc.centroid(d);
        return "translate(" + (c[0] + d.pullOutSize) + "," + c[1] + ")"
            + "rotate(" + (d.angle * 180 / Math.PI - 90) + ")"
            + "translate(" + 20 + ",0"
            + (d.angle > Math.PI ? "rotate(180)" : "")
    })
    .text(function(d, i){
        return Names[i];
    })
    .call(wrapChord, 100);

// Draw Inner Chords
wrapper.selectAll("path.chord")
    .data(chord.chords)
    .enter().append("path")
    .attr("class", "chord")
    .style("stroke", "none")
    .style("fill", "url(#animatedGradient)")
    .style("opacity", function(d){
        return (Names[d.source.index] === "" ? 0 : opacityDefault);
    })
    .style("pointer-events", function(d, i){
        return (Names[d.source.index] === "" ? "none": "auto");
    })
    .attr("d", path)
    .on("mouseover", fadeOnChord)
    .on("mouseout", fade(opacityDefault));

// Other functions
function startAngle(d){
    return d.startAngle + offset;
}

function endAngle(d){
    return d.endAngle + offset;
}

function fade(opacity){
    return function(d, i){
        wrapper.selectAll("path.chord")
        .filter(function(d){
            return d.source.index !== i && d.target.index !== i && Names[d.source.index] !== "";
        })
        .transition()
        .style("opacity", opacity);
    };
}

function fadeOnChord(d){
    var chosen = d;
    wrapper.selectAll("path.chord")
        .transition()
        .style("opacity", function(d){
            return d.source.index === chosen.source.index && d.target.index === chosen.target.index ? opacityDefault : opacityLow;
        });
}

function wrapChord(text, width){
    text.each(function(){
        var text = d3.selection(this);
        var words = text.text().split(/\s+/).reverse();
        var word;
        var line = [];
        var lineNumber = 0;
        var lineHeight = 1.1;
        var y = 0;
        var x = 0;
        var dy = parseFloat(text.attr("dy"));
        var tspan = text.text(null).append("tspan")
            .attr("x", x)
            .attr("y", y)
            .attr("dy", dy + "em");

        while(word = words.pop()){
            line.push(word);
            tspan.text(line.join(" "));
            if(tspan.node().getComputedTextLength() > width){
                line.pop();
                tspan.text(line.join(" "));
                line = [word];
                tspan = text.append("tspan")
                    .attr("x", x)
                    .attr("y", y)
                    .attr("dy", ++lineNumber * lineHeight + dy + "em")
                    .text(word);
            }
        }
    });
}



}