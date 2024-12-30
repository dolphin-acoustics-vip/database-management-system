/**
 * Make an AJAX request to the specified URL with the specified data.
 * @param {string} url The URL to make the request to.
 * @param {string} method The HTTP method to use (e.g. 'GET', 'POST', 'PUT', 'DELETE').
 * @param {Object} data The data to send with the request.
 * @param {string} contentType The content type of the request.
 * @param {boolean} error_popups Whether to display error messages in popups.
 * @param {boolean} message_popups Whether to display message messages in popups.
 * @param {function} successCallback A callback function to call if the request is successful.
 * The function will be called with the response object as its first argument.
 * @param {function} errorCallback A callback function to call if the request fails.
 * The function will be called with the xhr object, status string, and error string as its arguments.
 */
function makeAjaxRequest(url, method, data, contentType = "application/x-www-form-urlencoded; charset=UTF-8", error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
  $.ajax({
      url: url,
      method: method,
      data: data,
      contentType: contentType,
      success: function(response) {
        console.log(response)
        if (response.errors && response.errors.length > 0) {
          const errorMessage = response.errors.join('\n');
          if (error_popups) {
            alert( "Error(s) occurred: " + errorMessage);
          }
          response.errors = null;
        }
        else if (response.messages && response.messages.length > 0) {
          const errorMessage = response.messages.join('\n');
          if (error_popups) {
            alert( "Info: " + errorMessage);
          }
        }
        if (successCallback) {
          successCallback(response);
        }
        if (response.redirect) {
          window.location.href = response.redirect;
        }
      },
      error: function(xhr, status, error) {
        alert('An error occurred: ' + error);
        if (errorCallback) {
          errorCallback(xhr, status, error);
        }
      }
    });
  }

  function makeAjaxRequestForm(form, error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
    var url = form.action;
    var method = form.method;
    var data = {};
    Array.prototype.forEach.call(form.elements, function(element) {
      if (element.name) {
        data[element.name] = element.value;
      }
    });
    console.log("I GOT HERE")
    makeAjaxRequest(url, method, data, error_popups, message_popups, successCallback, errorCallback);
  }

  function ajaxifyForm(form, error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
    form.addEventListener('submit', function(event) {
      event.preventDefault();
      makeAjaxRequestForm(form, error_popups, message_popups, successCallback, errorCallback);
    });
  }