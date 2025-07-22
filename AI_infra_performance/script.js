document.addEventListener('DOMContentLoaded', () => {
    const methodologies = [
        { name: 'Batching', description: 'Group similar tasks together to reduce overhead.' },
        { name: 'Caching', description: 'Store results of expensive computations to reuse them later.' },
        { name: 'Pre-computation', description: 'Perform computations in advance to provide quick access to results.' },
        { name: 'Laziness', description: 'Defer computations until they are actually needed.' },
        { name: 'Relaxation', description: 'Trade off precision for performance by relaxing constraints.' },
        { name: 'Contextualization', description: 'Use context-specific information to optimize performance.' },
        { name: 'Hardware Specialization', description: 'Leverage specialized hardware to accelerate tasks.' },
        { name: 'Layering', description: 'Organize the system into layers to manage complexity and optimize performance.' }
    ];

    const grid = document.querySelector('.methodology-grid');

    methodologies.forEach(method => {
        const div = document.createElement('div');
        div.className = 'methodology';
        div.innerHTML = `<h3>${method.name}</h3><p>${method.description}</p>`;
        grid.appendChild(div);
    });
});
