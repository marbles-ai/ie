/*
            Custom Chord Function

            Adjusted by Tom Tracy
                    from
            Nadieh Bremer's Adjustment
                    of
            Mike's Bostock's function
*/

stretchedChord = function(){

    var source = d3_source;
    var target = d3_target;
    var radius = d3_svg_chordRadius;
    var startAngle = d3_svg_arcStartAngle;
    var endAngle = d3_svg_arcEndAngle;
    var pullOutSize = 0;

    var π = Math.PI;
    var halfπ = π / 2;

    function subgroup(self, f, d, i){

        var subgroup = f.call(self, d, i);
        var r = radius.call(self, subgroup, i);
        var a0 = startAngle.call(self, subgroup, i) - halfπ;
        var a1 = endAngle.call(self, subgroup, i) - halfπ;

        return{
            r: r,
            a0: [a0],
            a1: [a1],
            p0: [ r * Math.cos(a0), r * Math.sin(a0)],
            p1: [ r * Math.cos(a1), r * Math.sin(a1)]
        };
    }

    function arc(r, p, a){

        var sign = (p[0] >= 0 ? 1 : -1);

        return "A" + r + "," + r + " 0 " + +(a > π) + ",1" + (p[0] + sign * pullOutSize) + "," + p[1];
    }

    function curve(p1){

        var sign = (p1[0] >= 0 ? 1 : -1);

        return "Q 0,0 " + (p1[0] + sign * pullOutSize) + "," + p1[1];
    }

    function chord(d, i){

        var s = subgroup(this, source, d, i);
        var t = subgroup(this, target, d, i);

        return "M" + (s.p0[0] + pullOutSize) + "," + s.p0[1] +
            arc(s.r, s.p1, s.a1 - s.a0) +
            curve(t.p0) +
            arc(t.r, t.p1, t.a1 - t.a0) +
            curve(s.p0) +
            "Z";
    }

    chord.radius = function(v){

        if(!arguments.length){
            return radius;
        }

        radius = d3_functor(v);
        return chord;
    };

    chord.pullOutSize = function(v){

        if(!arguments.length){
            return pullOutSize;
        }

        pullOutSize = v;
        return chord;
    };

    chord.source = function(v){

        if(!arguments.length){
            return source;
        }

        source = d3_functor(v);
        return chord;
    };

    chord.target = function(v){

        if(!arguments.length){
            return target;
        }

        target = d3_functor(v);
        return chord;
    };

    chord.startAngle = function(v){

        if(!arguments.length){
            return startAngle;
        }

        startAngle = d3_functor(v);
        return chord;
    };

    chord.endAngle = function(v){

        if(!arguments.length){
            return endAngle;
        }

        endAngle = d3_functor(v);
        return chord;
    };

    function d3_svg_chordRadius(d){
        return d.radius;
    }

    function d3_source(d){
        return d.source;
    }

    function d3_target(d){
        return d.target;
    }

    function d3_svg_arcStartAngle(d){
        return d.startAngle;
    }

    function d3_svg_arcEndAngle(d){
        return d.endAngle;
    }

    function d3_functor(v){

        return typeof v === "function" ? v : function(){
            return v;
        };
    }

    return chord;
}