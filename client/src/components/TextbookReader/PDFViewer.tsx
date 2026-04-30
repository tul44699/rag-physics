import { useState, useCallback, useMemo } from "react";
import { pdfjs, Document, Page } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import styles from "./PDFViewer.module.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
	"pdfjs-dist/build/pdf.worker.min.mjs",
	import.meta.url,
).toString();

interface Props {
	file: string;
	page: number;
	onPageLoadSuccess: (pdf: { numPages: number }) => void;
	onPageChange: (page: number) => void;
}

export default function PDFViewer({ file, page, onPageLoadSuccess }: Props) {
	const [zoom, setZoom] = useState(1.2);
	const [docError, setDocError] = useState<string | null>(null);

	const docOptions = useMemo(
		() => ({
			httpHeaders: { Authorization: `Bearer ${localStorage.getItem("token")}` },
		}),
		[],
	);

	const handleDocError = useCallback(() => {
		setDocError("Failed to load PDF. The file may be missing or corrupted.");
	}, []);

	if (docError) {
		return <div className={styles.error}>{docError}</div>;
	}

	return (
		<div className={styles.container}>
			<div className={styles.zoomBar}>
				<button
					onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
					className={styles.zoomBtn}
				>
					-
				</button>
				<span className={styles.zoomLabel}>{Math.round(zoom * 100)}%</span>
				<button
					onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
					className={styles.zoomBtn}
				>
					+
				</button>
			</div>
			<Document
				file={file}
				onLoadSuccess={onPageLoadSuccess}
				onLoadError={handleDocError}
				loading={<div className={styles.loading}>Loading PDF...</div>}
				error={<div className={styles.error}>Failed to load PDF.</div>}
				options={docOptions}
			>
				<Page
					pageNumber={page}
					scale={zoom}
					renderTextLayer={true}
					renderAnnotationLayer={true}
					loading={<div className={styles.loading}>Loading page {page}...</div>}
				/>
			</Document>
		</div>
	);
}
