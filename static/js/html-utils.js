/**
 * Adds shift-click and select-all functionality to a list of checkboxes.
 * @param {NodeList} checkboxes - A NodeList of HTML checkboxes.
 * @example
 * const checkboxes = document.querySelectorAll('input[name="selections-checkboxes"]');
 * addShiftClickFunctionality(checkboxes);
 */
function addShiftClickFunctionality(checkboxes) {
    let lastChecked;
  
    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener('click', function (event) {
        // Shift-click functionality
        if (event.shiftKey && lastChecked) {
          const start = Array.prototype.indexOf.call(checkboxes, lastChecked);
          const end = Array.prototype.indexOf.call(checkboxes, checkbox);
          const checkboxesToCheck = Array.prototype.slice.call(checkboxes, Math.min(start, end), Math.max(start, end) + 1);
  
          checkboxesToCheck.forEach((checkbox) => {
            checkbox.checked = true;
          });
        }
  
        // Select-all functionality
        if (checkbox.classList.contains('select-all')) {
          checkboxes.forEach((checkbox) => {
            checkbox.checked = checkbox === event.target ? event.target.checked : event.target.checked;
          });
        }
  
        lastChecked = event.target;
      });
    });
  }

  /**
   * Add event listener to a delete button. When clicked, it gets the values of all
   * checked checkboxes, sets the values of all selected checkboxes in a hidden input 
   * field, and submits a form.
   * @param {NodeList} checkboxes - The checkboxes
   * @param {HTMLElement} button - The button that will trigger the submission
   * @param {HTMLElement} input - The hidden input field that will store the values of selected checkboxes
   * @param {HTMLFormElement} form - The form that will be submitted
   */
  function addCheckboxFormSubmission(checkboxes, button, input, form) {
    // Add event listener to the delete button
    button.addEventListener('click', () => {
        // Get the checked checkboxes
        const checkedCheckboxes = Array.from(checkboxes).filter(checkbox => checkbox.checked);
        
        // Get the file IDs of the checked checkboxes
        const selectedValues = checkedCheckboxes.map(checkbox => checkbox.value);

        // Set the file IDs in the hidden input field
        input.value = selectedValues.join(',');

        // Submit the form
        form.submit();
    });
  }

  function uploadFormWithProgress(formId, progressBarId, progressTextId) {
    const form = document.getElementById(formId);
    const progressBar = document.getElementById(progressBarId);
    const progressText = document.getElementById(progressTextId);
  
    form.addEventListener('submit', (e) => {
      progressBar.style="display: block";
      progressText.style="display: block";
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.value = percent;
        progressText.textContent = `${percent}%`;
      });
  
      const formData = new FormData(form);
      xhr.open(form.method, form.action, true);
      xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE) {
          if (xhr.status === 200) {
            const redirectUrl = xhr.responseURL;
            if (redirectUrl) {
              window.location.href = redirectUrl;
            }
          }
        }
      };
      xhr.send(formData);
    });
  }
  




  // function uploadFormWithProgress(formId, progressBarId, progressTextId, url) {
  //   const form = document.getElementById(formId);
  //   const progressBar = document.getElementById(progressBarId);
  //   const progressText = document.getElementById(progressTextId);
  //   const submitButton = form.querySelector('button[type="submit"]');
  
  //   submitButton.addEventListener('click', (e) => {
  //     e.preventDefault();
  //     const xhr = new XMLHttpRequest();
  //     xhr.upload.addEventListener('progress', (e) => {
  //       const percent = Math.round((e.loaded / e.total) * 100);
  //       progressBar.value = percent;
  //       progressText.textContent = `${percent}%`;
  //     });
  
  //     const formData = new FormData(form);
  //     xhr.open('POST', url, true);
  //     xhr.onreadystatechange = () => {
  //       if (xhr.readyState === XMLHttpRequest.DONE) {
  //         if (xhr.status === 200) {
  //           const redirectUrl = xhr.responseURL;
  //           if (redirectUrl) {
  //             window.location.href = redirectUrl;
  //           }
  //         }
  //       }
  //     };
  //     xhr.send(formData);
  //   });
  // }