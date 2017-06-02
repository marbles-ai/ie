/**
 * Created by tjt7a on 5/28/17.
 */

function generatedata(title, content, when, who) {
    return "<a href='#' class='list-group-item list-group-item-action flex-column align-items-start'>"
    + "<div class='d-flex w-100 justify-content-between'>"
    + "<h5 class='mb-1'>" + title + "</h5>"
    + "<small>" + when + "</small>"
    + "</div>"
    + "<p class='mb-1'>" + content + "</p>"
    + "<small>" + who + "</small>"
    + "</a>";
}


function addData(title, content) {
    $('#inputlist').append(generatedata(title, content, 'time', 'who'));
}


for (i = 0; i < 100; i++) {
    var title = 'Article: ' + i;
    var content = 'Content: ' + i;
    console.log("Writing new argument to list");
    addData(title, content);
}