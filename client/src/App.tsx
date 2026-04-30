import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ConversationProvider } from "./context/ConversationContext";
import { GeneratedContentProvider } from "./context/GeneratedContentContext";
import { ProfileProvider } from "./context/ProfileContext";
import { TextbookProvider } from "./context/TextbookContext";
import Layout from "./components/Layout";
import LoginPage from "./components/LoginPage";
import ProtectedRoute from "./components/ProtectedRoute";
import FormulaSheet from "./components/FormulaSheet";
import TextbookLibrary from "./components/TextbookLibrary/TextbookLibrary";
import TextbookReader from "./components/TextbookReader/TextbookReader";

export default function App() {
	return (
		<AuthProvider>
			<Routes>
				<Route path="/login" element={<LoginPage />} />
				<Route element={<ProtectedRoute />}>
					<Route
						path="/*"
						element={
							<ProfileProvider>
								<ConversationProvider>
									<TextbookProvider>
										<GeneratedContentProvider>
											<Layout>
												<Routes>
													<Route path="/" element={<TextbookLibrary />} />
													<Route
														path="/textbooks/:textbookId"
														element={<TextbookReader />}
													/>
													<Route
														path="/formulasheet"
														element={<FormulaSheet />}
													/>
												</Routes>
											</Layout>
										</GeneratedContentProvider>
									</TextbookProvider>
								</ConversationProvider>
							</ProfileProvider>
						}
					/>
				</Route>
			</Routes>
		</AuthProvider>
	);
}
