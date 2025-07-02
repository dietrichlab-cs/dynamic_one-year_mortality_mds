import {useState} from 'react'
import './App.css'
import CsvDropZone from "./components/CsvDropZone.jsx";

function App() {
    const [model, setModel] = useState("longitudinal");
    const [karyotype, setKaryotype] = useState("");
    const [age, setAge] = useState("");
    const [gender, setGender] = useState("m");
    const [blasts, setBlasts] = useState("");
    const [fileData, setFileData] = useState([]);
    const [csvString, setCsvString] = useState("");
    const [easix, setEasix] = useState("");
    const [hbEd, setHbEd] = useState("");
    const [leukoEd, setLeukoEd] = useState("");
    const [survivalTime, setSurvivalTime] = useState("");

    const [uploadedFile, setUploadedFile] = useState(null);
    const [errors, setErrors] = useState({});
    const [predictionResult, setPredictionResult] = useState(null);
    const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);

    const karyotypeOptions = {
        0: "0 - Very Low",
        1: "1 - Low",
        2: "2 - Intermediate",
        3: "3 - High",
        4: "4 - Very High",
    };

    const handleCsvUpload = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (evt) => {
            const text = evt.target.result;
            const lines = text.trim().split("\n");
            const header = lines[0].split(",").map(h => h.trim());

            const expectedHeader = [
                "day_from_diagnosis",
                "leukocytes",
                "erythrocytes",
                "hematocrit",
                "thrombocytes",
                "hemoglobin"
            ];

            const isValidHeader = new Set(header).size === expectedHeader.length && expectedHeader.every(col => header.includes(col));
            if (!isValidHeader) {
                alert("Invalid CSV header.");
                return;
            }

            setCsvString(text);
            setUploadedFile(file); // ✅ mark that file is uploaded

            const rows = lines.slice(1, 21).map(line => {
                const values = line.split(",");
                return Object.fromEntries(header.map((h, i) => [h, values[i]]));
            });
            setFileData(rows);
        };

        reader.readAsText(file);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const newErrors = {};
        if (!model) newErrors.model = "Model is required";
        if (!age) newErrors.age = "Age is required";
        if (!gender) newErrors.gender = "Gender is required";
        let formData;
        if (model === "longitudinal") {
            formData = await submitLongitudinalModel(newErrors)
        } else if (model === "baseline") {
            formData = await submitBaselineModel(newErrors)
        } else {
            if (Object.keys(newErrors).length > 0) {
                setErrors(newErrors);
                return;
            }
        }
        if (formData !== null) await predict(formData)
    };

    const submitLongitudinalModel = async (newErrors) => {
        if (!csvString.trim()) newErrors.csv = "CSV data is required";
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return null;
        }
        setErrors({});  // Clear previous errors
        return {
            model,
            karyotype: karyotype === "" ? null : parseInt(karyotype),
            age: parseFloat(age),
            gender,
            blasts: blasts === "" ? null : parseFloat(blasts),
            csv: csvString,
            easix: null,
            hb_ed: null,
            leuko_ed: null,
            survival_time: null
        };
    }

    const submitBaselineModel = async (newErrors) => {
        if (!survivalTime) newErrors.model = "Survival time is required";
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return null;
        }
        setErrors({});  // Clear previous errors
        return {
            model,
            karyotype: karyotype === "" ? null : parseInt(karyotype),
            age: parseFloat(age),
            gender,
            blasts: blasts === "" ? null : parseFloat(blasts),
            csv: csvString,
            easix: easix ? parseFloat(easix) : null,
            hb_ed: hbEd ? parseFloat(hbEd) : null,
            leuko_ed: leukoEd ? parseFloat(leukoEd) : null,
            survival_time: parseInt(survivalTime)
        };
    }

    const predict = async (formData) => {
        const url = import.meta.env.VITE_API_URL;
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(formData),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail);
            }
            const data = await response.json();
            setPredictionResult(data.prediction);  // 👈 Save the prediction
        } catch (error) {
            console.error("Prediction failed:", error);
            alert("Prediction failed: " + error.message);
        }
    }
    if (!disclaimerAccepted) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center p-8">
                <div className="max-w-4xl w-full bg-gray-100 p-6 rounded shadow overflow-y-auto max-h-screen">
                    <h1 className="text-2xl font-bold mb-4">Disclaimer</h1>
                    <div className="text-sm text-gray-700 space-y-4">
                        <p>
                            The web implementation of this mortality and complications risk calculator ("prediction
                            tool"), linked from the website of the dietrichlab group, complements the scientific article
                            'Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical
                            Data' by Bobak et al. (2025) not yet published. The prediction tool is based on the models
                            described in the article and is intended for research or demonstration purposes only.
                        </p>
                        <p>
                            The prediction tool is not to be used as a substitute for medical advice, diagnosis, or
                            treatment of any health condition or problem. Users of the prediction tool should not rely
                            on information provided by the prediction tool for their own health problems. Questions
                            should be addressed to your own physician or other healthcare provider. Moreover, the
                            prediction tool does not predict whether a single patient will die within one-year after
                            prediction, because this is influenced by a large variety of genetic and acquired factors,
                            some of which may still be unknown.
                        </p>
                        <p>
                            The authors make no warranties, nor express or implied representations whatsoever, regarding
                            the accuracy, completeness, timeliness, comparative or controversial nature, or usefulness
                            of any information contained or referenced in the prediction tool. The authors do not assume
                            any risk whatsoever for your use of the prediction tool or the information contained herein.
                            Health-related information changes frequently and therefore information contained in the
                            prediction tool may be outdated, incomplete or incorrect.
                        </p>
                        <p>
                            Use of the prediction tool does not create an express or implied physician-patient
                            relationship. The activities and products of the authors and their developers and agents are
                            not endorsed by our past, present, or future employers. The authors do not record specific
                            prediction tool user information and do not contact users of the prediction tools.
                        </p>
                        <p>
                            You are hereby advised to consult with a physician or other professional healthcare provider
                            prior to making any decisions, or undertaking any actions or not undertaking any actions
                            related to any healthcare problem or issue you might have at any time, now or in the future.
                            In using the prediction tools, you agree that neither the authors nor any other party is or
                            will be liable or otherwise responsible for any decision made or any action taken or any
                            action not taken due to your use of any information presented in the prediction tool.
                        </p>
                    </div>
                    <div className="mt-6 text-center">
                        <button
                            onClick={() => setDisclaimerAccepted(true)}
                            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            I Acknowledge and Accept
                        </button>
                    </div>
                </div>
            </div>
        );
    }
    return (
        <div className="min-h-screen flex flex-col bg-gray-100">
            {/* Main content fills available space */}
            <main className="flex-grow">
                <div className="w-full grid grid-cols-3 gap-4 p-6 bg-gray-100">
                    {/* Left Column: Form */}
                    <form
                        className="col-span-2 w-full grid grid-cols-20 space-y-4 bg-white py-6 ps-6 pe-1 rounded shadow"
                        onSubmit={handleSubmit}>
                        {/* Form fields go here */}
                        <div className="space-y-4 col-span-19">
                            {/* All your inputs/selects/upload etc */}
                            <h2 className="text-xl font-bold mb-4">Patient Data Input</h2>
                            <p>Fields marked with * are always required</p>

                            <div>
                                <label className="block font-medium">Model *</label>
                                <select value={model} onChange={(e) => {
                                    setModel(e.target.value);
                                    setCsvString("");
                                    setFileData([])
                                    setUploadedFile(null)
                                }}
                                        className="w-full mt-1 p-2 border rounded">
                                    <option value="baseline">Baseline</option>
                                    <option value="longitudinal">Longitudinal</option>
                                </select>
                                {errors.model && <p className="text-red-500 text-sm mt-1">{errors.model}</p>}
                            </div>

                            <div>
                                <label className="block font-medium">Bone-Marrow Blasts %</label>
                                <input type="number" step="0.1" min="0" max="100" value={blasts}
                                       onChange={(e) => setBlasts(e.target.value)}
                                       className="w-full mt-1 p-2 border rounded"/>
                            </div>

                            <div>
                                <label className="block font-medium">IPSSR Karyotype Classification (0-4)</label>
                                <select value={karyotype} onChange={(e) => setKaryotype(e.target.value)}
                                        className="w-full mt-1 p-2 border rounded">
                                    <option value="">-- Select --</option>
                                    {Object.entries(karyotypeOptions).map(([value, label]) => (
                                        <option key={value} value={value}>{label}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block font-medium">Age *</label>
                                <input type="number" step="0.01" min="0" value={age}
                                       onChange={(e) => setAge(e.target.value)}
                                       className="w-full mt-1 p-2 border rounded"/>
                                {errors.age && <p className="text-red-500 text-sm mt-1">{errors.age}</p>}
                            </div>

                            <div>
                                <label className="block font-medium">Gender *</label>
                                <select value={gender} onChange={(e) => setGender(e.target.value)}
                                        className="w-full mt-1 p-2 border rounded">
                                    <option value="m">Male</option>
                                    <option value="f">Female</option>
                                </select>
                                {errors.gender && <p className="text-red-500 text-sm mt-1">{errors.gender}</p>}
                            </div>
                            {model === "baseline" && (
                                <div>
                                    <label className="block font-medium">EASIX Score</label>
                                    <input type="number" step="0.5" min="0" value={easix}
                                           onChange={(e) => setEasix(e.target.value)}
                                           className="w-full mt-1 p-2 border rounded"/>
                                </div>
                            )}
                            {model === "baseline" && (
                                <div>
                                    <label className="block font-medium">Leukocytes at diagnosis (x1000/μl)</label>
                                    <input type="number" step="0.1" min="0" value={leukoEd}
                                           onChange={(e) => setLeukoEd(e.target.value)}
                                           className="w-full mt-1 p-2 border rounded"/>
                                </div>
                            )}
                            {model === "baseline" && (
                                <div>
                                    <label className="block font-medium">HB at diagnosis (g/dl)</label>
                                    <input type="number" step="0.1" min="0" value={hbEd}
                                           onChange={(e) => setHbEd(e.target.value)}
                                           className="w-full mt-1 p-2 border rounded"/>
                                </div>
                            )}
                            {model === "baseline" && (
                                <div>
                                    <label className="block font-medium">Survival time in days *</label>
                                    <input type="number" step="0.01" min="0" value={survivalTime}
                                           onChange={(e) => setSurvivalTime(e.target.value)}
                                           className="w-full mt-1 p-2 border rounded"/>
                                    {errors.survivalTime &&
                                        <p className="text-red-500 text-sm mt-1">{errors.survivalTime}</p>}
                                </div>
                            )}
                            {model === "longitudinal" && (uploadedFile ? (
                                <div className="mt-4 space-y-2">
                                    <p className="text-sm text-gray-600">Uploaded: {uploadedFile.name}</p>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setUploadedFile(null);
                                            setFileData([]);
                                            setCsvString("");
                                        }}
                                        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                                    >
                                        Clear File
                                    </button>
                                </div>
                            ) : (
                                <CsvDropZone onFileAccepted={(file) => handleCsvUpload({target: {files: [file]}})}/>
                            ))}
                            {model === "longitudinal" && errors.csv &&
                                <p className="text-red-500 text-sm mt-1">{errors.csv}</p>}

                            {model === "longitudinal" && fileData.length > 0 && (
                                <div className="overflow-x-auto mt-4 border">
                                    <table className="min-w-full text-sm text-left">
                                        <thead className="bg-gray-200">
                                        <tr>
                                            {Object.keys(fileData[0]).map((key) => (
                                                <th key={key} className="p-2">{key}</th>
                                            ))}
                                        </tr>
                                        </thead>
                                        <tbody>
                                        {fileData.map((row, idx) => (
                                            <tr key={idx} className="border-t">
                                                {Object.values(row).map((val, i) => (
                                                    <td key={i} className="p-2">{val}</td>
                                                ))}
                                            </tr>
                                        ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                        {/* Submit button: vertical, rotated text */}
                        <div className="col-span-1 flex justify-center ms-2 p-5">
                            <button
                                type="submit"
                                className="w-full h-full bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center justify-center"
                            >
             <span className="transform -rotate-90 origin-center whitespace-nowrap tracking-wider">
               Predict
             </span>
                            </button>
                        </div>
                    </form>
                    {/* Right Column: Prediction Output */}
                    <div className="col-span-1 bg-white p-6 rounded shadow flex flex-col items-center justify-center">
                        <h2 className="text-lg font-bold mb-4">Prediction Result</h2>

                        {predictionResult !== null ? (
                            <>
                                {/* Color bar */}
                                <div
                                    className="relative w-full h-8 rounded bg-gradient-to-r from-green-400 via-yellow-300 to-red-500 mt-2 mb-4">
                                    {/* Marker */}
                                    <div
                                        className="absolute top-0 h-8 w-1 bg-black"
                                        style={{
                                            left: `${Math.min(100, Math.max(0, predictionResult * 100))}%`,
                                            transform: 'translateX(-50%)'
                                        }}
                                    />
                                </div>
                                {/* Numeric value */}
                                <div className="text-center text-gray-700 text-xl font-semibold">
                                    {Math.round(predictionResult * 1000) / 10}%<br/> predicted probability for 1-year
                                    mortality
                                </div>
                            </>
                        ) : (
                            <p className="text-gray-500">No prediction yet</p>
                        )}
                    </div>
                </div>
            </main>
            {/* Footer Disclaimer */}
            <footer
                className="fixed bottom-0 left-0 w-full bg-gray-200 text-center text-xs text-gray-600 p-4 shadow-inner"> The
                predictions and models presented on this page are for research or demonstration purposes only.
                They are not intended for clinical use, and no guarantees are made regarding their accuracy or
                correctness. This tool supplements the scientific article 'Dynamic Mortality Risk Prediction in
                Myelodysplastic Syndromes Using Longitudinal Clinical Data' by Bobak et al. (2025) not yet published.
            </footer>
        </div>
    );
}

export default App
