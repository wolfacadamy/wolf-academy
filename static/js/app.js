// ── Wolf Academy LMS — Frontend JavaScript ──────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initFlashMessages();
    initMarkdownPreview();
    initQuizForm();
    initDeleteConfirms();
});


// ── Flash Messages (auto-dismiss) ───────────────────────────────────

function initFlashMessages() {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        // Click to dismiss
        flash.addEventListener('click', () => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(100px)';
            setTimeout(() => flash.remove(), 300);
        });
        // Auto dismiss after 5s
        setTimeout(() => {
            if (flash.parentNode) {
                flash.style.opacity = '0';
                flash.style.transform = 'translateX(100px)';
                setTimeout(() => flash.remove(), 300);
            }
        }, 5000);
    });
}


// ── Markdown Live Preview ───────────────────────────────────────────

function initMarkdownPreview() {
    const editor = document.getElementById('md-editor');
    const preview = document.getElementById('md-preview');

    if (!editor || !preview) return;

    function updatePreview() {
        // Simple client-side Markdown → HTML for preview purposes
        let text = editor.value;

        // Headings
        text = text.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
        text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // Bold and Italic
        text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Code blocks
        text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Blockquotes
        text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // Unordered lists
        text = text.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

        // Ordered lists 
        text = text.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        // Horizontal rules
        text = text.replace(/^---$/gm, '<hr>');

        // Links
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

        // Paragraphs
        text = text.replace(/^(?!<[a-z])((?!^\s*$).+)$/gm, '<p>$1</p>');

        // Line breaks
        text = text.replace(/\n\n/g, '<br>');

        preview.innerHTML = text || '<p style="color: var(--text-muted);">Preview will appear here...</p>';
    }

    editor.addEventListener('input', updatePreview);
    updatePreview(); // initial render
}


// ── Quiz Form Interactions ──────────────────────────────────────────

function initQuizForm() {
    const quizForm = document.getElementById('quiz-form');
    if (!quizForm) return;

    // Highlight selected options
    quizForm.addEventListener('change', (e) => {
        if (e.target.type === 'radio') {
            const name = e.target.name;
            const labels = quizForm.querySelectorAll(`input[name="${name}"]`);
            labels.forEach(input => {
                input.closest('.option-label').classList.remove('selected');
            });
            e.target.closest('.option-label').classList.add('selected');
        }
    });

    // Confirm submission
    quizForm.addEventListener('submit', (e) => {
        const questions = quizForm.querySelectorAll('.question-card');
        let unanswered = 0;

        questions.forEach(qCard => {
            const inputs = qCard.querySelectorAll('input[type="radio"]');
            const answered = Array.from(inputs).some(i => i.checked);
            if (!answered) unanswered++;
        });

        if (unanswered > 0) {
            e.preventDefault();
            alert(`You have ${unanswered} unanswered question(s). Please answer all questions before submitting.`);
        }
    });
}


// ── Delete Confirmations ────────────────────────────────────────────

function initDeleteConfirms() {
    document.querySelectorAll('.confirm-delete').forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!confirm('Are you sure you want to delete this? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}
