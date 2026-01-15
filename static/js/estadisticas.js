document.addEventListener('DOMContentLoaded', function() {
    let chartByCarrera = null;
    let chartTituladosVsNo = null;

    const filterCarrera = document.getElementById('filterCarrera');

    function populateCarreras() {
        if (!filterCarrera) return;
        fetch('/consulta_carrera')
            .then(res => res.json())
            .then(carreras => {
                carreras.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id_carrera;
                    opt.textContent = c.nombre_carrera;
                    filterCarrera.appendChild(opt);
                });
            })
            .catch(err => console.error('Error al cargar carreras:', err));
    }

    function loadCharts(id_carrera) {
        const query = id_carrera ? `?id_carrera=${id_carrera}` : '';

        // Titulados por carrera (barra)
        fetch(`/api/titulados_por_carrera${query}`)
            .then(response => response.json())
            .then(data => {
                const labels = data.map(r => r.nombre || 'Sin carrera');
                const values = data.map(r => Number(r.total || 0));

                if (chartByCarrera) chartByCarrera.destroy();
                const ctx = document.getElementById('chartByCarrera').getContext('2d');
                chartByCarrera = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Titulados',
                            data: values,
                            backgroundColor: (function(){
                                const palette = ['#0d6efd','#6610f2','#20c997','#0dcaf0','#198754','#6c757d','#ffc107','#6f42c1','#0b7285','#66101f'];
                                return labels.map((_, i) => palette[i % palette.length]);
                            })(),
                            borderColor: 'rgba(0,0,0,0.05)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                    }
                });
            })
            .catch(err => console.error('Error al obtener titulados por carrera:', err));

        // Resumen por estatus (dona)
        fetch(`/api/titulados_resumen${query}`)
            .then(response => response.json())
            .then(data => {
                const titulados = Number(data.titulados || 0);
                const enProceso = Number(data.en_proceso || 0);
                const noTitulados = Number(data.no_titulados || 0);

                if (chartTituladosVsNo) chartTituladosVsNo.destroy();
                const ctx2 = document.getElementById('chartTituladosVsNo').getContext('2d');
                chartTituladosVsNo = new Chart(ctx2, {
                    type: 'doughnut',
                    data: {
                        labels: ['Titulados', 'En proceso', 'No titulados'],
                        datasets: [{
                            data: [titulados, enProceso, noTitulados],
                            backgroundColor: ['#198754', '#ffc107', '#dc3545']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' },
                            title: { display: true, text: 'Estatus de titulación' }
                        }
                    }
                });
            })
            .catch(err => console.error('Error al obtener resumen de titulados:', err));
    }

    populateCarreras();
    loadCharts();

    if (filterCarrera) {
        filterCarrera.addEventListener('change', function() {
            loadCharts(this.value);
        });
    }
});