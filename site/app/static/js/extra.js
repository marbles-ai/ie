$(document).ready(function() {
  // Apply opacity to all children of .iconwapper when hovering 
  $(".iconwrapper").children().hover(function() {
      $(this).addClass("iconhover");
    }, function() {
        $(this).removeClass("iconhover");
    });
});