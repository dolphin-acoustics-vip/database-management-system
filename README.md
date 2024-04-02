> ⚠️ **warning:** this project is still in a developmental stage. Some sections of the code and/or documentation may be incomplete.

# Dolphin Acoustics VIP Database Management System

This Database Management System (DBMS) is a project that aims to streamline the data pipeline of the Dolphin Acoustics VIP (the Project) at the University of St Andrews.

## Glossary

- **Markdown**: A lightweight markup language with plain-text formatting syntax. <a id="markdown"></a>
- **GPT**: Generative Pre-trained Transformer, a type of deep learning model developed by OpenAI. <a id="gpt"></a>


## Project description
The DBMS was developed to store a range of files at various spots in the data pipeline of the Project:
- storage of raw audio recordings (wav)
- storage of selections of the recordings (wav)
- storage of summary selection tables (csv)
- storage of contours of the selections (csv)
- storage of contour summaries
- export of contour files in contour
- quality assurance at each stage of the pipeline **Markdown** d





[requirements.txt](requirements.txt)




<script>
    document.addEventListener('DOMContentLoaded', function() {
        const glossaryLinks = document.querySelectorAll('.glossary-link');
        
        glossaryLinks.forEach(link => {
            const term = link.textContent.trim().toLowerCase();
            const id = term.replace(/\s+/g, '-');
            link.href = `#${id}`;
        });
    });
</script>