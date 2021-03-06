$(document).ready(function() {
    disable_fields();
    add_refresh_btn();
    reorder_elements();
    $('[id$=notes]').placeholder();

    $(window).resize(function() {
        reorder_elements();
    });

    $("[id$='_search']").on("click", function(e) {
        e.preventDefault();

        var form = $('#saved-search-form');

        data = form.serialize();
        data = data.replace('=on','=True').replace('=off','=False');
        data = data.replace('undefined', 'None');
        $.ajax({
            data: data,
            type: 'POST',
            url: '/saved-search/view/save/',
            success: function(data) {
                if (data == '') {
                    window.location = '/saved-search/view/';
                } else {
                    add_errors(data);
                }
            }
        });
    });

    $(".refresh").on( "click", function(e) { validate(e) } );
    $("#id_edit_url").on( "input keypress cut paste", function(e) { validate(e) } );

});

function validate(e) {
    if (e.target == $('[id$="url"]').get(0)) {
        if (this.timer) {
            clearTimeout(this.timer);
        }
        var pause_interval = 1000;
        // Take a little longer due to mobile requiring a keyboard
        // to come up onto screen, change keyboard views, ect.
        if($(window).width() < 500){
            pause_interval = 3000;
        }
        this.timer = setTimeout(function() {
            do_validate();
        }, pause_interval);
    } else {
        do_validate();
    }
}

function do_validate() {
    var csrf_token = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var url = $('[id$="url"]').val();
    validation_status('validating...')
    $.ajax({
        type: "POST",
        url: "/saved-search/view/validate-url/",
        data: { csrfmiddlewaretoken: csrf_token,
                action: "validate",
                url: url},
        success: function(data) {
            var json = jQuery.parseJSON(data);
            if (json.url_status == 'valid') {
                validation_status(json.url_status);
                if ($('[id$="label"]').val().length == 0) {
                    $('[id$="label"]').val(json.feed_title);
                }
                if ($('[id$="feed"]').val() != json.rss_url) {
                    $('[id$="feed"]').val(json.rss_url);
                }
                enable_fields();
                date_select();
            }
            else {
                validation_status(json.url_status);
            }
        }
    });
}

function validation_status(status) {
    var label_text;

    if (status == 'valid') {
        label_text = 'label-success';
    } else {
        label_text = 'label-important';
    }
    if ($('#validated').length) {
        $('#validated').removeClass('label-success');
        $('#validated').removeClass('label-important');
        $('#validated').addClass(label_text);
        $('#validated').text(status);
    } else {
        $('[class~=refresh]').after(
            '<div id="validated" class="label '+
            label_text+'">'+status+'</div>');
    }
    reorder_elements();
}

function add_refresh_btn() {
    var field = $('[id$="url"]');
    field.parent().addClass('input-append');

    var field_width = field.width() - 28;
    field.css("width", String(field_width)+"px");

    field.after('<span class="btn add-on refresh"><i class="icon icon-refresh">');
}

function disable_fields() {
    // Disable/hide fields until valid URL is entered
    if ($('[id$="url"]').val() == '') {
        $('[id^="id_edit_sort_by_"]').hide();
        $('label[for^="id_edit_sort_by_"]').hide();
        $('[id$="label"]').hide();
        $('label[for$="label"]').hide();
        $('[id$="is_active"]').hide();
        $('label[for$="is_active"]').hide();
        $('[id$="email"]').hide();
        $('label[for$="email"]').hide();
        $('[id$="account_activation_message"]').hide();
        $('label[for$="account_activation_message"]').hide();
        $('[id$="frequency"]').hide();
        $('label[for$="frequency"]').hide();
        $('[id$="notes"]').hide();
        $('label[for$="notes"]').hide();
        $('[id$="day_of_week"]').hide();
        $('[id$="day_of_month"]').hide();
        $('label[for$="day_of_week"]').hide();
        $('label[for$="day_of_month"]').hide();
        $('.save').hide();
    } else {
        enable_fields();
        date_select();
    }
}

function enable_fields() {
    $('[id^="id_edit_sort_by_"]').show();
    $('label[for^="id_edit_sort_by_"]').css('display', 'inline-block');
    $('[id$="label"]').show();
    $('label[for$="label"]').show();
    $('[id$="is_active"]').show();
    $('label[for$="is_active"]').show();
    $('[id$="email"]').show();
    $('label[for$="email"]').show();
    $('[id$="frequency"]').show();
    $('label[for$="frequency"]').show();
    $('[id$="notes"]').show();
    $('label[for$="notes"]').show();
    $('[id$="day_of_week"]').show();
    $('[id$="day_of_month"]').show();
    $('label[for$="day_of_week"]').show();
    $('label[for$="day_of_month"]').show();
    $('.save').show();
}

function reorder_elements() {
    var width = $(document).width();
    var url_container = $('#mobile-url-container');
    if (width > 500) {
        if (url_container.length) {
            url_container.after(url_container.children());
            url_container.remove();
        }
        $('[id$=_url]').parent().removeClass('flush-bottom');
        $('label[for$=_url]').parent().removeClass('url-label-alignment');
        $('[id$=_url] + .refresh').after($('#validated'));
        $('label[for$=is_active]').parent().after($('[id$=is_active]').parent());
        $('label[for$=label]').parent().show();
        $('label[for$=notes]').parent().show();
    } else {
        if (!url_container.length) {
            $('[id$=_url]').parent().after('<div id="mobile-url-container"></div>');
            url_container = $('#mobile-url-container');
        }
        $('#mobile-url-container').append($('label[for$=_url]').parent());
        $('#mobile-url-container').append($('[id$=_url]').parent());
        $('[id$=_url]').parent().addClass('flush-bottom')
        $('label[for$=_url]').parent().addClass('url-label-alignment');
        $('label[for$=_url]').append($('#validated'));
        $('label[for$=is_active]').parent().before($('[id$=is_active]').parent());
        $('label[for$=label]').parent().hide();
        $('label[for$=notes]').parent().hide();
    }
}
