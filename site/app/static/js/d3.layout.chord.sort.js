/*
            Custom Chord Layout Function

            Adjusted by Tom Tracy
                    from
            Nadieh Bremer's Adjustment
                    of
            Mike's Bostock's function
*/

newChordLayout = function(){
    var ε = 1e-6;
    var ε2 = ε * ε;
    var π = Math.PI;
    var τ = 2 * π;
    var τε = τ - ε;
    var halfπ = π / 2;
    var d3_radians = π / 180;
    var d3_degrees = 180 / π;

    var chord = {};
    var chords, groups, matrix, n, sortGroups, sortSubgroups, sortChords;
    var padding = 0;

    function relayout(){
        var subgroups = {};
        var groupSums = [];
        var groupIndex = d3.range(n);
        var subgroupIndex = [];
        var k, x, x0, i, j;

        chords = [];
        groups = [];
        k = 0, i = -1;

        // Add up the sizes of each member in each group
        while(++i < n){
            x = 0, j = -1;
            while(++j < n){
                x += matrix[i][j];
            }
            groupSums.push(x);
            subgroupIndex.push(d3.range(n).reverse());
            k += x;
        }

        // Sort the groups
        if(sortGroups){
            groupIndex.sort(function(a, b){
                return sortGroups(groupSums[a], groupSums[b]);
            });
        }

        // Sort the subgroups
        if(sortSubgroups){
            subgroupIndex.forEach(function(d, i){
                d.sort(function(a, b){
                    return sortSubgroups(matrix[i][a], matrix[i][b]);
                });
            });
        }

        k = (τ - padding * n) / k;
        x = 0, i = -1;

        while(++i < n){
            x0 = x, j = -1;

            while(++j < n){
                var di = groupIndex[i];
                var dj = subgroupIndex[di][j];
                var v = matrix[di][dj];
                var a0 = x;
                var a1 = x += v * k;

                subgroups[di + "-" + dj] = {
                    index: di,
                    subindex: dj,
                    startAngle: a0,
                    endAngle: a1,
                    value: v
                };
            }

            groups[di] = {
                index: di,
                startAngle: x0,
                endAngle: x,
                value: (x - x0) / k
            };
            x += padding;
        }

        i = -1;

        while(++i < n){

            j = i - 1;

            while(++j < n){

                var source = subgroups[i + "-" + j];
                var target = subgroups[j + "-" + i];

                if(source.value || target.value){
                    chords.push(source.value < target.value ? {
                        source: target,
                        target: source
                    } : {
                        source: source,
                        target: target
                    });
                }
            }
        }

        if(sortChords){
            resort();
        }
    }

    function resort(){
        chords.sort(function(a, b){
            return sortChords((a.source.value + a.target.value) / 2,
                              (b.source.value + b.target.value) / 2);
        });
    }

    chord.matrix = function(x){
        if(!arguments.length){
            return matrix;
        }
        n = (matrix = x) && matrix.length;
        chords = groups = null;
        return chord;
    };

    chord.padding = function(x){
        if(!arguments.length){
            return padding;
        }
        padding = x;
        chords = groups = null;
        return chord;
    };

    chord.sortGroups = function(x){
        if(!arguments.length){
            return sortGroups;
        }
        sourtGroups = x;
        chords = groups = null;
        return chord;
    };

    chord.sortSubgroups = function(x){
        if(!arguments.length){
            return sortSubgroups;
        }
        sortSubgroups = x;
        chords = null;
        return chord;
    };

    chord.sortChords = function(x){
        if(!arguments.length){
            return sortChords;
        }
        sortChords = x;
        if(chords){
            resort();
        }
        return chord;
    };

    chord.chords = function(){
        if(!chords){
            relayout();
        }
        return chords;
    };

    chord.groups = function(){
        if(!groups){
            relayout();
        }
        return groups;
    };
    return chord;
};