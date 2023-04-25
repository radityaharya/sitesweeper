import logging
import os
from pathlib import Path
import threading
from typing import List

import pdfkit
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from requests.adapters import HTTPAdapter
from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.table import Column
from rich.logging import RichHandler

logger = logging.getLogger("website-crawler-to-pdf")
logger.setLevel(logging.DEBUG)

text_column = TextColumn("{task.description}", table_column=Column(ratio=5))
bar_column = BarColumn(bar_width=None, table_column=Column(ratio=1))
percent_column = TextColumn("{task.percentage:>3.1f}%", table_column=Column(ratio=1))
tasks_column = TextColumn(
    "[progress.description]{task.completed} of {task.total}[progress.description]",
    justify="right",
    table_column=Column(ratio=1),
)


class Crawler:
    def __init__(self, start_url: str, base_path: str, depth: int, output_path: str):
        self.start_url = start_url
        self.base_path = base_path
        self.depth = depth
        self.output_path = output_path
        self.all_links = []
        self.console = Console()
        self.session = requests.Session()
        self.adapter = HTTPAdapter(max_retries=5)
        self.session.mount("http://", self.adapter)
        self.session.mount("https://", self.adapter)
        self.progress = Progress(
            text_column,
            bar_column,
            percent_column,
            tasks_column,
            console=self.console,
            transient=True,
            auto_refresh=True,
        )
        self.main_task = self.progress.add_task("Crawling...", total=None)

    def crawl_link(
        self,
        url: str,
    ) -> None:
        with self.progress:
            if self.depth == 0:
                return
            if url in self.all_links:
                return
            self.progress.update(self.main_task, description=f"Crawling {url}")

            if self.is_valid_url(url):
                self.all_links.append(url)

            try:
                response = self.session.get(url, timeout=5)
            except:
                logger.error(f"Error: Cannot access the URL {url}")
                return

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a")
            link_urls = []
            for link in links:
                if "href" in link.attrs:
                    link_url = link.attrs["href"]
                    if link_url.startswith("/"):
                        link_url = self.start_url + link_url
                    if self.is_valid_url(
                        link_url,
                    ):
                        link_urls.append(link_url)
            threads = []
            for link_url in link_urls:
                t = threading.Thread(
                    target=self.crawl_link,
                    args=(link_url,),
                )
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

    def use_sitemap(
        self,
    ) -> List[str]:
        response = requests.get(self.start_url + "/sitemap.xml")
        soup = BeautifulSoup(response.text, features="xml")
        links = self.extract_sitemap_links(soup)
        for link in links:
            self.crawl_link(
                link,
            )
        return links

    def use_crawl_start_url(
        self,
    ) -> List[str]:
        self.crawl_link(
            self.start_url,
        )
        return self.all_links

    def is_valid_url(self, url: str) -> bool:
        if url.startswith("/"):
            url = self.start_url + url
        if not url.startswith(self.start_url):
            logger.debug(f"URL {url} does not match the start URL {self.start_url}")
            return False
        if "#" in url:
            logger.debug(f"URL {url} contains a fragment")
            return False
        if self.base_path not in url:
            logger.debug(f"URL {url} does not match the base path {self.base_path}")
            return False
        try:
            status_code = self.session.get(url, timeout=5).status_code
            if status_code != 200:
                logger.debug(f"URL {url} is not accessible")
                return False
        except:
            logger.debug(f"URL {url} is not accessible")
            return False
        return True

    def extract_sitemap_links(self, soup: BeautifulSoup) -> list:
        for link in soup.find_all("loc"):
            link_url = link.text
            self.all_links.append(link_url)
        return self.all_links

    def remove_invalid_urls(
        self,
    ) -> None:
        for link in self.all_links:
            if not self.is_valid_url(link):
                self.all_links.remove(link)

    def merge_pdfs(self) -> None:
        try:
            merger = PdfMerger(strict=False)
            pdfs = []
            with self.progress:
                task = self.progress.add_task("Merging PDFs...", total=None)
                self.progress.update(
                    task, total=len(list(Path(self.output_path).glob("*.pdf")))
                )
                for pdf_path in Path(self.output_path).rglob("*.pdf"):
                    self.progress.update(
                        task, description=f"found {pdf_path.name}", total=len(pdfs) + 1
                    )
                    pdfs.append(str(pdf_path))
                self.progress.update(
                    task, description="Merging PDFs...", completed=len(pdfs)
                )
                pdfs = self.sort_links(pdfs)
                for pdf in pdfs:
                    merger.append(pdf)
                merged_file_path = Path(self.output_path) / "merged.pdf"
                with merged_file_path.open(mode="wb") as f:
                    merger.write(f)
                merger.close()
                self.progress.remove_task(task)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    def sort_links(self, links: list) -> List[str]:
        groups = {}
        for link in links:
            prefix = "/".join(link.split("/")[:-1])
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(link)
        sorted_links = []
        for prefix in sorted(groups.keys()):
            sorted_links.extend(sorted(groups[prefix]))
        return sorted_links

    def generate_pdf(
        self,
        link: str,
        options: dict,
        task: TaskID,
    ) -> None:
        try:
            if link.startswith("/"):
                link = self.start_url + link

            path = "/".join(link.split("/")[3:-1])
            if path:
                output_dir = Path(self.output_path) / path
                output_file = output_dir / (link.split("/")[-1] + ".pdf")
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_file = Path(self.output_path) / (link.split("/")[-1] + ".pdf")
            
            pdfkit.from_url(link, str(output_file), options=options)
            self.progress.update(task, advance=1)
        except Exception as e:
            logger.error(f"Error: Cannot generate PDF for {link}")
            logger.error(e, exc_info=True)

    def generate_pdfs(
        self,
        options: dict,
    ) -> None:
        if not os.path.exists(self.output_path):
            os.mkdir(self.output_path)

        with Live(self.progress, refresh_per_second=1):
            task = self.progress.add_task("Generating PDFs", total=len(self.all_links))
            threads = []
            for link in self.all_links:
                self.progress.update(task, description=f"Generating PDF for {link}")
                logger.debug(f"Generating PDF for {link}")

                thread = threading.Thread(
                    target=self.generate_pdf,
                    args=(link, options, task),
                )
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()