function createErrorToast(heading="Unable to continue", text) {
    $.toast({
        heading: heading,
        text: text,
        icon: 'error',
        showHideTransition: 'slide',
        position: 'top-right',
    });
}

