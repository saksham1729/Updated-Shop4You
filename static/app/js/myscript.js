$(document).ready(function () {
    console.log("myscript.js loaded ✅");

    // Utility function to update minus buttons disable state based on quantity
    function updateMinusButtons() {
        $('.minus-cart').each(function () {
            var qty = parseInt(this.parentNode.children[2].innerText);
            if (qty <= 1) {
                $(this).css({
                    'pointer-events': 'none',
                    'opacity': '0.5',
                    'cursor': 'not-allowed'
                });
            } else {
                $(this).css({
                    'pointer-events': 'auto',
                    'opacity': '1',
                    'cursor': 'pointer'
                });
            }
        });
    }

    $('#slider1, #slider2, #slider3').owlCarousel({
        loop: true,
        margin: 20,
        responsiveClass: true,
        responsive: {
            0: {
                items: 1,
                nav: false,
                autoplay: true,
            },
            600: {
                items: 3,
                nav: true,
                autoplay: true,
            },
            1000: {
                items: 5,
                nav: true,
                loop: true,
                autoplay: true,
            }
        }
    });

    updateMinusButtons(); // Disable minus buttons at page load if quantity == 1

    $('.plus-cart').click(function () {
        var id = $(this).attr("pid").toString();
        var qtyElem = this.parentNode.children[2];

        $.ajax({
            type: "GET",
            url: "/pluscart",
            data: { prod_id: id },
            success: function (data) {
                qtyElem.innerText = data.quantity;
                document.getElementById("amount").innerText = data.amount.toFixed(2);
                document.getElementById("totalamount").innerText = data.totalamount.toFixed(2);
                $('#cart-item-count').text(data.totalitem);

                updateMinusButtons();  // re-enable minus button if quantity > 1
            }
        });
    });

    $('.minus-cart').click(function () {
        var id = $(this).attr("pid").toString();
        var qtyElem = this.parentNode.children[2];
        var cartItemRow = $(this).closest('.row');

        $.ajax({
            type: "GET",
            url: "/minuscart",
            data: { prod_id: id },
            success: function (data) {
                if (data.quantity > 0) {
                    qtyElem.innerText = data.quantity;
                } else {
                    cartItemRow.remove();
                }
                document.getElementById("amount").innerText = data.amount.toFixed(2);
                document.getElementById("totalamount").innerText = data.totalamount.toFixed(2);
                $('#cart-item-count').text(data.totalitem);

                updateMinusButtons();

                if ($('.row').length === 0) {
                    $('.card-body h3').text('Your Cart is Empty.');

                    if (data.totalitem === 0) {
                        $('#cart-item-count').text('0');
                    }
                }
            }
        });
    });

    $('.remove-cart').click(function () {
        var id = $(this).attr("pid").toString();
        var elm = this;

        $.ajax({
            type: "GET",
            url: "/removecart",
            data: { prod_id: id },
            success: function (data) {
                document.getElementById("amount").innerText = data.amount.toFixed(2);
                document.getElementById("totalamount").innerText = data.totalamount.toFixed(2);
                $('#cart-item-count').text(data.totalitem);

                $(elm).closest('.row').remove();

                if ($('.remove-cart').length === 0) {
                    $('#cart-item-count').text('0');
                    $('#cart-totals-section').remove();

                    let container = $('#cart-totals-section');
                    if (container.length === 0) {
                        container = $('.row').first();
                    } else {
                        container.empty();
                    }

                    container.append(`
                        <div class="text-center" id="empty-cart-message">
                            <h3 class="text-center">You have no Product in Your Cart</h3>
                            <div class="text-center mt-3">
                                <img src="/static/app/images/emptycart.png" alt="Empty cart" class="img-fluid w-25">
                            </div>
                        </div>
                    `);
                }
            }
        });
    });
});
