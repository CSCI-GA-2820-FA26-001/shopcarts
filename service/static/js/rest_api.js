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

$(function () {
    // ****************************************
    //  C L E A R   T H E   F O R M
    // ****************************************
    $("#clear-btn").click(function () {
        clear_form_data();
        flash_message("");
    });
});
