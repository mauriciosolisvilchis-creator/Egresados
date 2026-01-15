$(document).ready(function(){
    $('#consultar_usuarios').on('click',function(){
        $.ajax({
            url:'/consulta_egresados',
            method: 'GET',
            success: function(data){
               $('#actualizable').html(data); 
            },
            error:function(err){
                console.log('Error al cargar los alumnos')
            }

        });

    });
});

document.getElementById("btn_actualizar_egresado").addEventListener("click", function() {
    const formData = new FormData(document.getElementById("registro_egresado"));

    fetch("/registrar_egresado", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Egresado registrado exitosamente.");
            
            document.getElementById("registro_egresado").reset();

            const preview = document.getElementById("previewegr");
            if (preview) {
                preview.src = "/static/images/user.png";
            }

            const modalElement = document.getElementById("modalregistroegresado");
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
                
            }

        } else {
            alert("Error al registrar al egresado: " + data.message);
            
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error al enviar los datos.");
    });
});