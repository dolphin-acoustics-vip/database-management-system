/**
 * Sends an asynchronous HTTP request to a specified URL, using the provided method and data, 
 * while allowing for optional handling of success and error conditions via callbacks.
 * 
 * @param {string} url - The endpoint to which the request is sent.
 * @param {string} method - The HTTP method to use, such as 'GET', 'POST', etc.
 * @param {Object} data - The payload to be transmitted; can be a JSON object or FormData.
 * @param {string} contentType - Specifies the media type of the request payload; defaults to application/x-www-form-urlencoded (this should rarely be modified).
 * @param {boolean} error_popups - If true, error alerts are shown when the request fails.
 * @param {boolean} message_popups - If true, informational alerts are shown upon success.
 * @param {function} successCallback - Executed when the request completes successfully, receiving the response object
 * @param {function} errorCallback - Executed when the request fails (or completed with errors), receiving the response object
 * 
 * NOTE: When using FormData, contentType is automatically set to false to avoid jQuery conflicts.
 * 
 * NOTE: This function is designed to work with JSONRequest() in request_handler.py of the OCEAN flask application.
 * This will ensure responses are JSON objects containing {"messages": [], "errors": [], "redirect": "", data: {}}.
 * If anything else is returned, a generic error message will be shown using the JS alert() method.
 * 
 * The following are the mechanics of this method:
 * 
 * 1. The request is sent to the specified URL using the provided method and data.
 * 2. If error_popups or message_popups are true, their respective popups are shown (if messages or errors are returned in the response)
 * 3. If an errorCallback is provided and the request is unsuccessful OR errors are returned in the response, the errorCallback is called.
 * 4. If a successCallback is provided and the request is successful AND no errors are returned in the response, the successCallback is called.
 * 5. If a redirect link is returned in the response, the page is refreshed with that link.
 *
 * NOTE: for the error and message popups, the default JS alert() method is used if a redirect link is provided. Otherwise the method assumes the
 * page will not be refreshed making it safe to use the JQuery toast library.
 */
async function makeAjaxRequest(url, method, data, contentType = "application/x-www-form-urlencoded; charset=UTF-8", error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
  var ajaxSettings = await {
    url: url,
    method: method,
    data: data,
    /**
     * Handles the success response of an Ajax request by processing the response
     * object. Validates the response format to ensure it contains 'messages',
     * 'errors', and 'redirect' keys. Displays error or informational popups based
     * on the response content and configuration, and invokes the appropriate
     * callback functions if provided. Redirects the page if a redirect link is
     * included in the response.
     *
     * @param {Object} response - The response object expected from the server.
     * @param {Array} response.messages - An array of informational messages.
     * @param {Array} response.errors - An array of error messages, if any.
     * @param {string} response.redirect - A URL to redirect the page to, if provided.
     */
    success: async function(response) {
      var error = false;

      // Ensure response is in the form of a JSON object with 'messages', 'errors', and 'redirect' keys
      if (!(response instanceof Object) || !response.hasOwnProperty('messages') || !response.hasOwnProperty('errors') || !response.hasOwnProperty('redirect')) {
        await $.toast({
          heading: "Invalid response from the server",
          text: "The server did not return a valid response. This is likely due to an internal error or networking issue. Please contact your administrator.",
          icon: 'error',
          hideAfter: 5000,
          preventDuplicates: true,
          showHideTransition: 'slide',
          position: 'top-right',
        });        
        error = true;
      }
      // If there are errors in the response
      if (response.errors && response.errors.length > 0) {
        const errorMessage = response.errors.join('\n');
        // If error popups are enabled
        if (error_popups) {
          // If there is a redirect link in the response show the error
          // popup as an alert
          if (response.redirect) {
            alert( "The following issue(s) ocurred: " + errorMessage);
          }
          // If there is no redirect link in the response show the error
          // popup as a toast
          else {
            await $.toast({
              heading: response.errors.length === 1 ? response.errors[0] : "The following issue(s) occurred:",
              text: response.errors.length > 1 ? response.errors.slice(1) : "",
              icon: 'error',
              hideAfter: 5000,
              showHideTransition: 'slide',
              position: 'top-right',
            });
          }
        }
        error = true;
      }
      else if (response.messages && response.messages.length > 0) {
        const messages = response.messages.join('\n');
        // If message popups are enabled
        if (message_popups) {
          // If there is a redirect link in the response show the error
          // popup as an alert
          if (response.redirect) {
            alert( "Info: " + messages);
          }
          // If there is no redirect link in the response show the error
          // popup as a toast
          else {
            await $.toast({
              heading: response.messages.length === 1 ? response.messages[0] : "Info",
              text: response.messages.length > 1 ? response.messages.slice(1) : "",
              icon: 'info',
              hideAfter: 5000,
              showHideTransition: 'slide',
              position: 'top-right',
            });
          }
        }
      }
      // If there is an error callback method provided call it
      if (errorCallback && error) {
        await errorCallback(response);
      }
      // If there is a success callback method provided call it
      // ONLY if no error has ocurred
      if (successCallback && !error) {
        await successCallback(response);
      }
      // If there is a redirect link, refresh the page with it
      if (response.redirect) {
        window.location.href = response.redirect;
      }
    },
  // Handle any errors that may occur during the request
  // and alert the user with a message containing the error
    error: function(xhr, status, error) {
      alert('An error occurred: ' + error);
    }
  };

  if (data instanceof FormData) {
    ajaxSettings.contentType = false;
    ajaxSettings.processData = false;
  } else {
    ajaxSettings.contentType = contentType;
    ajaxSettings.processData = true;
  }

  await $.ajax(ajaxSettings);
}

  function makeAjaxRequestForm(form, error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
    var url = form.action;
    var method = form.method;
    var data = new FormData(form);
    makeAjaxRequest(url=url, method=method, data=data, contentType=undefined, error_popups=error_popups, message_popups=message_popups, successCallback=successCallback, errorCallback=errorCallback);
  }

  function ajaxifyForm(form, error_popups = true, message_popups = true, successCallback = null, errorCallback = null) {
    form.addEventListener('submit', function(event) {
      event.preventDefault();
      makeAjaxRequestForm(form, error_popups, message_popups, successCallback, errorCallback);
    });
  }