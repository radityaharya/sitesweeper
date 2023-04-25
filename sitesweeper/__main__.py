import argparse
import datetime
import logging
import os
import sys
from rich.logging import RichHandler

from .crawler import Crawler

logger = logging.getLogger("website-crawler-to-pdf")
logger.setLevel(logging.DEBUG)
logger.addHandler(RichHandler())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawl a website and generate a PDF file"
    )
    parser.add_argument("start_url", type=str, help="The starting URL for the crawl")
    parser.add_argument(
        "--base_path", type=str, default="/", help="The base path for the crawl"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        help="The output path for the PDF file (default: ./output)",
    )
    parser.add_argument(
        "--depth", type=int, default=100, help="The depth of the crawl (default: 100)"
    )
    parser.add_argument(
        "--use_sitemap",
        action="store_true",
        help="Use the sitemap.xml file to crawl the website",
    )
    parser.add_argument(
        "--merge_pdfs", action="store_true", help="Merge all PDF files into one"
    )
    parser.add_argument(
        "--javascript_delay",
        type=int,
        default=3000,
        help="The delay for javascript to load (default: 3000)",
    )
    parser.add_argument(
        "--page_size",
        type=str,
        default="A4",
        help="The page size for the PDF (default: A4)",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="UTF-8",
        help="The encoding for the PDF (default: UTF-8)",
    )
    parser.add_argument(
        "--log_level", type=str, default="INFO", help="The log level (default: INFO)"
    )
    args = parser.parse_args()

    if args.output_path is None:
        args.output_path = os.getcwd() + "/output"
    
    if args.start_url.endswith("/"):
        args.start_url = args.start_url[:-1]
    
    if not args.start_url.startswith("http"):
        logger.error("Start URL must start with http or https")
        sys.exit(1)

    if args.start_url.count("/") > 2:
        args.base_path = args.start_url.split("/", 3)[3]
        args.start_url = args.start_url.split("/", 3)[0] + "//" + args.start_url.split("/", 3)[2]

    starttime = datetime.datetime.now()
    
    crawler = Crawler(
        start_url=args.start_url,
        base_path=args.base_path,
        depth=args.depth,
        output_path=args.output_path,
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    logger = logging.getLogger("website-crawler-to-pdf")
    logger.setLevel(args.log_level)
    if not os.path.exists(args.output_path):
        logger.debug(f"Creating output directory: {args.output_path}")
        os.makedirs(args.output_path)

    all_links = []
    if args.use_sitemap:
        logger.debug("Using sitemap.xml")
        crawler.use_sitemap()
    else:
        logger.debug("Using crawl")
        crawler.use_crawl_start_url()

    all_links = crawler.all_links
    crawler.progress.update(crawler.main_task, description="Generating PDFs", total=None)
    logger.debug(f"Found {len(all_links)} links")
    options = {
        "page-size": args.page_size,
        "encoding": args.encoding,
        "javascript-delay": args.javascript_delay,
        "no-stop-slow-scripts": "",
        "disable-smart-shrinking": "",
        "viewport-size": "1920x1080",
        "load-error-handling": "ignore",
        "load-media-error-handling": "ignore",
        "margin-top": "0",
        "margin-right": "0",
        "margin-bottom": "0",
        "margin-left": "0",
        "quiet": "",
    }

    crawler.generate_pdfs(options)

    endtime = datetime.datetime.now()

    if args.merge_pdfs:
        logger.info("Merging PDFs")
        crawler.merge_pdfs()
        logger.info(f"Saved merged PDF to {args.output_path}/merged.pdf")
    else:
        logger.info(f"Generated {len(all_links)} PDFs, saved to {args.output_path}")

    totaltime_sec = (endtime - starttime).total_seconds()
    logger.info(f"Total time: {totaltime_sec} seconds")
