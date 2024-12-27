# MANUAL DE USO

1. Descargar el repositorio, ya sea mediante un git clone o descargandolo en formato .zip
2. Una vez descargado el repositorio ubicarlo donde el usuario prefiera.
3. Abrir una terminal con permisos de administrador
4. Instalar las dependencias ejecutando: pip install flask opencv-python-headless numpy pytesseract
5. Utilizando la Terminal posicionarse en la carpeta principal donde se descargó el repositorio y ejecutar con Python3 el archivo server.py "output: python3 server.py" dejar la ventana de la terminal abierta para seguir ejecutando el programa.
6. Abrir el navegador e ir a http://127.0.0.1:5000 para ejecutar la interfaz grafica princpial
7. Iniciar sesión con las siguientes credenciales user y pass: admin/admin
8. Dentro del menú principal se tiene el menú de dispositivos mediante el cual el usuario puede agregar mas camaras si asi lo desea. Por defecto viene agregada la primer camara que detecte del sistema. Tambien si el usuario lo desea puede cerrar sesión presionando el boton amarillo.
9. Cada camara agregada puede ser visualizada o eliminada mediante los botones indicativos.
10. Si desea visualizar la camara en tiempo real, luego de hacer click en "Visualizar" se abre una nueva ventana que muestra en pantalla la reprodución del video y tambien datos de texto como son: Patente, Distancia y Desviación. Todos estos datos son brindados por la camara. 
11. Calibración: La calibración es por dispositvo/camara, y se accede a ella a traves del menu de visualización presionando el boton "Calibrar nueva distancia". Para ello se debe estar leyendo en tiempo real una patente para que al tomar la distancia y hacer click en el boton, el programa guarde ese nuevo valor como su distancia referencia.
12. Visualización de alertas, para acceder a las alertas visuales el usuario debe acceder a http://127.0.0.1:5001/0 siendo 0 el indice que figura en el Menú principal debajo del nombre de la camara. Esto le permite al usuario visualizar alertas de multiples dispositvos.
13. Para finalizar el programa dirigirse a la terminal y ejecutar CTRL + C o cerrar la pestaña.


