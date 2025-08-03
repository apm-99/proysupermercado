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
from scraping import get_driver,create_driver,return_driver,str_findAll
import gc
# Pool de drivers reutilizable
driver_pool = Queue()
pool_lock = threading.Lock()

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
                EC.presence_of_element_located((By.CLASS_NAME, "vtex-store-components-3-x-productBrand--quickview"))
            )
        except TimeoutException:
            # Si no carga en 3 segundos, intenta parsear lo que hay
            pass
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Extraer datos de forma más eficiente
        nombre_elem = soup.find('span', class_=lambda c: c and "vtex-store-components-3-x-productBrand--quickview" in c)
        if not nombre_elem:
            return {}
            
        nombre_prod = nombre_elem.text.strip()
        
        precio_elem = soup.find('span', class_="valtech-carrefourar-product-price-0-x-currencyContainer")
        precio = precio_elem.text.replace('\xa0', ' ').strip() if precio_elem else "N/A"
        
        # Breadcrumbs - más robusto
        breadcrumbs = soup.find_all('a', class_=lambda c: c and 'vtex-breadcrumb-1-x-link' in c)
        categoria_gen = "N/A"
        
        if len(breadcrumbs) >= 2:
            categoria_gen = breadcrumbs[-1].text.strip()
        
        
        descuento = "Sin descuento"
        precio_anterior = "Sin precio anterior"
        
        elem = soup.find('span', class_="tooltipText")
        if elem and elem.text.strip():
            descuento = elem.text.strip()
            
        
        precio_ant_elem = soup.find('span', class_="valtech-carrefourar-product-price-0-x-listPriceValue strike")
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
        if driver:
            try:
                driver.quit()
            except:
                pass
        print(f"Error procesando {link}: {str(e)}")
        return {}

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

def scroll_para_cargar_productos(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    max_scrolls = 15
    scrolls_realizados = 0

    while scrolls_realizados < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls_realizados += 1


def getDFCarrefour():
    tiempo_inicio = time.time()
    
    # Inicializar pool de drivers
    num_drivers = 4 # Aumentado de 5 a 8
    for _ in range(num_drivers):
        try:
            driver_pool.put_nowait(create_driver())
        except:
            pass
    
    # Driver principal para navegación
    driver = create_driver()
    driver.set_page_load_timeout(15)
    
    # categorias = ["Cervezas", "Vinos","Fernet-y-aperitivos", "Gaseosas"]
    categorias = ["Gaseosas"]
    link_productos = []

    # Recolección de enlaces - fase más rápida
    print("Recolectando enlaces de productos...")
    for cat in categorias:
        base_url = f"https://www.carrefour.com.ar/Bebidas/{cat}?page="
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        productos_set = set()
        pagina = 1
        consecutivos_vacios = 0
        max_vacios = 2

        while consecutivos_vacios < max_vacios:
            url = base_url + str(pagina)
            driver.get(url)
            print(f"\nAccediendo a: {url}")
            time.sleep(2)

            scroll_para_cargar_productos(driver)

            nuevos_links = set()
            try:
                producto_divs = driver.find_elements(By.CSS_SELECTOR, 'div.valtech-carrefourar-search-result-3-x-galleryItem')
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
    
    return df,5

