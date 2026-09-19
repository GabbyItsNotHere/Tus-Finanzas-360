function toggleSidebar(){
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("expandida");
}

function toggleMenuTema(){
    const menu = document.getElementById('met');
    menu.classList.toggle('visible');
}

function cambiarTema(tema) {
    if(tema === 'oscuro'){
        document.body.classList.add('oscuro');
    } else {
        document.body.classList.remove('oscuro');
    }
    document.getElementById('met').classList.remove('visible');
}

function abrirModalAbono(event){
    // Captura el botón que disparó la función y lee los atributos seguros
    let boton = event.currentTarget;
    let idMeta = boton.getAttribute('data-id');
    let balanceDispo = boton.getAttribute('data-balance');

    document.getElementById("modalAbono").style.display = "flex";
    document.getElementById("id_meta").value = idMeta;
    
    // Asigna el límite máximo dinámicamente
    let inputMonto = document.getElementById("monto_aportado");
    inputMonto.max = balanceDispo;
}

function cerrarModalAbono(){
    document.getElementById("modalAbono").style.display = "none";
}


function abrirModalAbono(idMeta, balanceDispo){
    document.getElementById("modalAbono").style.display = "flex";
    
    // Asigna directamente el ID numérico recibido
    document.getElementById("id_meta").value = idMeta;
    
    // Asigna el límite máximo del input
    let inputMonto = document.getElementById("monto_aportado");
    inputMonto.max = balanceDispo;
}

function cerrarModalAbono(){
    document.getElementById("modalAbono").style.display = "none";
}