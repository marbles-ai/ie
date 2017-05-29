/**
 * Created by tjt7a on 5/28/17.
 */

var list = document.getElementById('inputlist');
var entry = document.createElement('li');

function addData(value) {
    var list = document.getElementById('inputlist');
    var entry = document.createElement('li');
    var title = document.createElement('div');
    var content = document.createElement('div');
    title.setAttribute('class', 'title');
    content.setAttribute('class', 'content');
    title.appendChild(document.createTextNode('Article: ' + value));
    content.appendChild(document.createTextNode('Content: ' + value));
    entry.appendChild(title);
    entry.appendChild(content);
    list.appendChild(entry);
}



for (i = 0; i < 100; i++) {
    addData(i);
}