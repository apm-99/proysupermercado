from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import gc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import os
import queue


# Pool de drivers reutilizable
driver_pool = Queue()
pool_lock = threading.Lock()




def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # AGREGAR ESTAS LÍNEAS PARA OCULTAR TODOS LOS LOGS:
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # Solo errores críticos
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-dev-shm-usage")
    # Las que ya tenías:
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option("useAutomationExtension", False)
    
    # MUY IMPORTANTE para ocultar logs:
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    
    # service = Service(log_path='/dev/null')  # En Linux/Mac
    # Redirigir stdout y stderr de ChromeDriver
    service = Service(ChromeDriverManager().install(), 
                    log_path=os.devnull)  # Esto evita logs al archivo
    service.creationflags = subprocess.CREATE_NO_WINDOW  # oculta ventana en Windows
    
    return webdriver.Chrome(options=options, service=service)



def get_driver():
    """Obtiene un driver del pool o crea uno nuevo"""
    try:
        return driver_pool.get_nowait()
    except queue.Empty:
        return create_driver()

def return_driver(driver):
    """Devuelve un driver al pool"""
    try:
        driver.delete_all_cookies()
        driver_pool.put_nowait(driver)
    except:
        try:
            driver.quit()
        except:
            pass

def str_findAll(lista):
    return lista[0].text if lista else ""

def obtener_datos_producto_optimizado(link):
    """Versión optimizada que reutiliza drivers y reduce tiempos de espera"""
    driver = None
    try:
        driver = get_driver()
        
        # Timeout más agresivo
        driver.set_page_load_timeout(20)
        driver.implicitly_wait(2)
        
        driver.get(link)
        # Espera mínima y más específica
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "vtex-store-components-3-x-productBrand"))
            )
        except TimeoutException:
            # Si no carga en 3 segundos, intenta parsear lo que hay
            pass
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Extraer datos de forma más eficiente
        driver.implicitly_wait(1)

        nombre_elem = soup.find('span', class_="vtex-store-components-3-x-productBrand")
        if not nombre_elem:
            return {}
            
        nombre_prod = nombre_elem.text.strip()
        
        precio_elem = soup.find('span', class_="valtech-gdn-dynamic-product-1-x-currencyContainer")
        precio = precio_elem.text.replace('\xa0', ' ').strip() if precio_elem else "N/A"
        
        # Breadcrumbs - más robusto
        breadcrumbs = soup.find_all('a', class_=lambda x: x and 'vtex-breadcrumb-1-x-link' in x)
        categoria_gen = "N/A"
        
        if len(breadcrumbs) >= 2:
            categoria_gen = breadcrumbs[1].text.strip()
        
        # Descuento - búsqueda más eficiente
        descuento_classes = [
            "valtech-gdn-dynamic-product-1-x-promoVolumenTxtTwo",
            "valtech-gdn-dynamic-product-1-x-weighableSavingsPercentage",
            "valtech-gdn-dynamic-product-1-x-weighableSavingsOnlyPercentage"
        ]
        
        descuento = "Sin descuento"
        precio_anterior = "Sin precio anterior"
        
        for cls in descuento_classes:
            elem = soup.find('span', class_=cls)
            if elem and elem.text.strip():
                descuento = elem.text.strip()
                break
        
        precio_ant_elem = soup.find('span', class_="mt4 valtech-gdn-dynamic-product-1-x-weighableListPrice valtech-gdn-dynamic-product-1-x-hasDecZero")
        if precio_ant_elem:
            precio_anterior = precio_ant_elem.text.replace('\xa0', ' ').strip()
        
        return_driver(driver)
        
        return {
            "Nombre": nombre_prod,
            "Precio": precio,
            "Descuento": descuento,
            "Precio anterior": precio_anterior,
            "Categoria": str(categoria_gen),
            "Link del producto": link
        }
        
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        print(f"Error procesando {link}: {str(e)}")
        return {}
def scroll_en_pagina(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(12):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "vtex-product-summary-2-x-container"))
        )
    except TimeoutException:
        pass



def procesar_productos_batch(productos_batch):
    """Procesa un lote de productos y reporta progreso"""
    resultados = []
    for i, producto in enumerate(productos_batch, 1):
        resultado = obtener_datos_producto_optimizado(producto)
        if resultado:
            resultados.append(resultado)
        print(f"Procesado {i}/{len(productos_batch)} productos del lote")
    gc.collect()
    return resultados

def scroll_en_pagina(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(12):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def getDF():
    tiempo_inicio = time.time()
    
    # Inicializar pool de drivers
    num_drivers = 4
    for _ in range(num_drivers):
        try:
            driver_pool.put_nowait(create_driver())
        except:
            pass
    categorias = ["gaseosas"]
    # categorias = ["gaseosas","cervezas"]
    for cat in categorias:
        base_url = f"https://www.masonline.com.ar/{cat}?page="
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10)

        productos_set = set()
        pagina = 1
        consecutivos_vacios = 0
        max_vacios = 2

        while consecutivos_vacios < max_vacios:
            url = base_url + str(pagina)
            driver.get(url)
            print(f"\nAccediendo a: {url}")
            time.sleep(2)

            scroll_en_pagina(driver)

            nuevos_links = set()
            try:
                producto_divs = driver.find_elements(By.CSS_SELECTOR, 'div.valtech-gdn-search-result-0-x-galleryItem')
                for div in producto_divs:
                    try:
                        a_tag = div.find_element(By.CSS_SELECTOR, 'a[href*="/p"]')
                        link = a_tag.get_attribute('href')
                        nuevos_links.add(link)
                    except:
                        continue
            except:
                pass

            nuevos_detectados = nuevos_links - productos_set
            print(f"Página {pagina}: {len(nuevos_detectados)} productos nuevos")

            if nuevos_detectados:
                productos_set.update(nuevos_detectados)
                consecutivos_vacios = 0
            else:
                consecutivos_vacios += 1

            pagina += 1

        print(f"\nTotal de productos únicos detectados: {len(productos_set)}")
        driver.quit()

    # Procesar con paralelización
    link_productos = list(productos_set)
    batch_size = 15
    batches = [link_productos[i:i+batch_size] for i in range(0, len(link_productos), batch_size)]

    articulos = []
    with ThreadPoolExecutor(max_workers=num_drivers) as executor:
        futures = {executor.submit(procesar_productos_batch, batch): i for i, batch in enumerate(batches)}

        for future in as_completed(futures):
            batch_num = futures[future]
            try:
                resultados = future.result()
                articulos.extend(resultados)
            except Exception as e:
                print(f"Error en batch {batch_num}: {str(e)}")

            if batch_num % 5 == 0:
                print("♻️ Reiniciando drivers del pool...")
                while not driver_pool.empty():
                    try:
                        d = driver_pool.get_nowait()
                        d.quit()
                    except:
                        pass
                for _ in range(num_drivers):
                    try:
                        driver_pool.put_nowait(create_driver())
                    except:
                        pass

    while not driver_pool.empty():
        try:
            driver = driver_pool.get_nowait()
            driver.quit()
        except:
            pass

    df = pd.DataFrame([art for art in articulos if art])
    if not df.empty:
        df.to_excel("Super_Optimizado.xlsx", index=False)
    else:
        print("No se obtuvieron datos")

    tiempo_final = time.time()
    tiempo_total = tiempo_final - tiempo_inicio
    print(f"\nTIEMPO TOTAL: {tiempo_total:.2f} segundos")
    
    return df, 4

def cleanup():
    while not driver_pool.empty():
        try:
            driver = driver_pool.get_nowait()
            driver.quit()
        except:
            pass