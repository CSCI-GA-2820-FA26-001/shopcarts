/*
 * Shared code for the Shopcarts admin page.
 *
 * Each button gets its click handler in its own story: create (#69),
 * retrieve (#70), update (#71), delete (#72), list (#73), search (#53)
 * and checkout (#56). Only Clear is set up here.
 */

// The Shopcart API. This becomes "/api/shopcarts" once #54 is merged.
const BASE_URL = "/shopcarts";

// ****************************************
//  U T I L I T Y   F U N C T I O N S
// ****************************************

// Fills the form with a Shopcart from the API
function update_form_data(shopcart) {
    $("#shopcart_id").val(shopcart.id);
    $("#shopcart_user_id").val(shopcart.user_id);
    $("#shopcart_status").val(shopcart.status);
}

// Empties every field of the form
function clear_form_data() {
    $("#shopcart_id").val("");
    $("#shopcart_user_id").val("");
    $("#shopcart_status").val("");
}

// Shows a message in the flash message area
function flash_message(message) {
    $("#flash_message").text(message);
}

// Replaces the rows of the results table with a list of Shopcarts
function update_results(shopcarts) {
    const rows = shopcarts.map((shopcart) =>
        $("<tr>").append(
            $("<td>").text(shopcart.id),
            $("<td>").text(shopcart.user_id),
            $("<td>").text(shopcart.status),
        )
    );
    $("#search_results tbody").empty().append(rows);
}

// Returns the message of an error response from the API
function error_message(xhr) {
    if (xhr.responseJSON && xhr.responseJSON.message) {
        return xhr.responseJSON.message;
    }
    return `Server error: ${xhr.status}`;
}

// Shows the Shopcarts of a customer in the results table, or every
// Shopcart when user_id is empty. Returns the request so callers can
// add their own done() handler.
function load_results(user_id) {
    const query = user_id ? `?user_id=${encodeURIComponent(user_id)}` : "";

    // Clear the old message so a step can't match it before this request ends
    flash_message("");
    return $.ajax({
        type: "GET",
        url: BASE_URL + query,
    })
        .done(function (shopcarts) {
            update_results(shopcarts);
            flash_message("Success");
        })
        .fail(function (xhr) {
            update_results([]);
            flash_message(error_message(xhr));
        });
}

$(function () {
    // ****************************************
    //  C L E A R   T H E   F O R M
    // ****************************************
    $("#clear-btn").click(function () {
        clear_form_data();
        flash_message("");
    });

    // ****************************************
    //  S E A R C H   B Y   C U S T O M E R
    // ****************************************
    $("#search-btn").click(function () {
        load_results($("#shopcart_user_id").val().trim()).done(function (shopcarts) {
            // Fill the form with the first result, so a cart can be found by its customer
            if (shopcarts.length > 0) {
                update_form_data(shopcarts[0]);
            } else {
                $("#shopcart_id").val("");
                $("#shopcart_status").val("");
            }
        });
    });

    // ****************************************
    //  R E T R I E V E   A   S H O P C A R T
    // ****************************************
    $("#retrieve-btn").click(function () {
        const shopcart_id = $("#shopcart_id").val().trim();
        if (!shopcart_id) {
            flash_message("Enter a Shopcart ID to retrieve");
            return;
        }

        flash_message("");
        $.ajax({
            type: "GET",
            url: `${BASE_URL}/${encodeURIComponent(shopcart_id)}`,
        })
            .done(function (shopcart) {
                update_form_data(shopcart);
                flash_message("Success");
            })
            .fail(function (xhr) {
                // Keep the ID that was typed, but drop the details of the last cart
                $("#shopcart_user_id").val("");
                $("#shopcart_status").val("");
                flash_message(error_message(xhr));
            });
    });

    // ****************************************
    //  L I S T   A L L   S H O P C A R T S
    // ****************************************
    $("#list-btn").click(function () {
        load_results("");
    });
});
