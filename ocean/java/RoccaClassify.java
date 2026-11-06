// Copyright (c) 2024
//
// This file is part of OCEAN.
//
// OCEAN is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// OCEAN is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

package rocca;

import java.io.*;
import java.util.*;
import weka.classifiers.AbstractClassifier;
import weka.core.DenseInstance;
import weka.core.Instances;
import weka.core.Utils;

/**
 * Runs a PAMGuard ROCCA whistle classifier (.model file) on contour statistics
 * calculated by OCEAN. Launched by ocean/app/classifier.py with Java's
 * single-file source launcher, so it needs no build step:
 *
 *   java -cp weka.jar RoccaClassify.java info <model>
 *   java -cp weka.jar RoccaClassify.java classify <model> < stats.csv
 *
 * `info` prints one JSON object describing the model.
 *
 * `classify` reads CSV from stdin. The first column is `id` and the remaining
 * columns are ROCCA parameter names (e.g. FREQMAX, DCMEAN). It prints one JSON
 * line per row containing the raw votes of every classifier stage. Unlike
 * PAMGuard, every stage is always run (following the top-voted species), and
 * the threshold is applied afterwards by OCEAN. This means threshold changes
 * never require the model to be run again.
 *
 * The classification follows RoccaRFModel.classifyContour and
 * RoccaClassifier.setAttributes in PAMGuard (src/rocca).
 */
public class RoccaClassify {

    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !(args[0].equals("info") || args[0].equals("classify"))) {
            System.err.println("Usage: RoccaClassify (info|classify) <model file>");
            System.exit(2);
        }
        Object[] loaded;
        try {
            loaded = loadModelFile(args[1]);
        } catch (Exception e) {
            System.err.println("Unable to read the file as a ROCCA classifier model (" + e + ")");
            System.exit(1);
            return;
        }
        String description = (String) loaded[0];
        RoccaRFModel model = (RoccaRFModel) loaded[1];
        if (args[0].equals("info")) printInfo(description, model);
        else classify(model);
    }

    /**
     * Load a ROCCA model file. Like RoccaClassifier.setUpClassifier there are two
     * formats, each containing two serialised objects:
     *   - original: [AbstractClassifier, Instances]
     *   - multi-stage: [String description, RoccaRFModel]
     */
    static Object[] loadModelFile(String path) throws Exception {
        List<Object> objects = new ArrayList<>();
        try (ObjectInputStream in = new LocalObjectInputStream(new BufferedInputStream(new FileInputStream(path)))) {
            while (true) {
                try { objects.add(in.readObject()); }
                catch (EOFException e) { break; }
            }
        }
        if (objects.size() < 2) throw new IOException("Model file must contain two objects, found " + objects.size());
        if (objects.get(0) instanceof String) {
            return new Object[] { objects.get(0), (RoccaRFModel) objects.get(1) };
        }
        AbstractClassifier classifier = (AbstractClassifier) objects.get(0);
        Instances dataset = (Instances) objects.get(1);
        return new Object[] { null, new RoccaRFModel(classifier, dataset, new RoccaRFModel[dataset.numClasses()]) };
    }

    static void printInfo(String description, RoccaRFModel model) {
        Set<String> attributes = new LinkedHashSet<>();
        List<String> species = new ArrayList<>();
        int[] stages = {0};
        collectInfo(model, attributes, species, stages);
        System.out.println("{\"description\":" + json(description)
                + ",\"stages\":" + stages[0]
                + ",\"attributes\":" + json(attributes)
                + ",\"species\":" + json(species) + "}");
    }

    /** Same traversal as RoccaRFModel.generateSpList, also collecting attribute names. */
    static void collectInfo(RoccaRFModel model, Set<String> attributes, List<String> species, int[] stages) {
        stages[0]++;
        Instances d = model.trainedDataset;
        for (int i = 0; i < d.numAttributes(); i++) {
            if (i != d.classIndex()) attributes.add(d.attribute(i).name().toUpperCase(Locale.ENGLISH));
        }
        for (int i = 0; i < d.numClasses(); i++) {
            if (model.modelList[i] == null) species.add(d.classAttribute().value(i));
            else collectInfo(model.modelList[i], attributes, species, stages);
        }
    }

    static void classify(RoccaRFModel model) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        PrintStream out = new PrintStream(new BufferedOutputStream(System.out), false);
        String headerLine = reader.readLine();
        if (headerLine == null) return;
        List<String> header = Arrays.asList(headerLine.trim().split(",", -1));
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.trim().isEmpty()) continue;
            String[] values = line.trim().split(",", -1);
            String id = values[0];
            try {
                StringBuilder stages = new StringBuilder("[");
                RoccaRFModel stage = model;
                while (stage != null) {
                    double[] votes = stage.roccaClassifierModel.distributionForInstance(toInstance(stage.trainedDataset, header, values));
                    if (stages.length() > 1) stages.append(",");
                    stages.append("{\"classes\":").append(json(Arrays.asList(stage.thisSpList)))
                          .append(",\"votes\":").append(Arrays.toString(votes)).append("}");
                    stage = stage.modelList[Utils.maxIndex(votes)];
                }
                out.println("{\"id\":" + json(id) + ",\"stages\":" + stages + "]}");
            } catch (Exception e) {
                out.println("{\"id\":" + json(id) + ",\"error\":" + json(String.valueOf(e.getMessage())) + "}");
            }
        }
        out.flush();
    }

    /**
     * Build a Weka instance for one stage, as RoccaClassifier.setAttributes does:
     * each non-class attribute is matched by its upper-cased name. Nominal attributes
     * (e.g. FREQBEGSWEEP) are passed as the index of the nominal value, which is how
     * both ROCCA and OCEAN store them (down=0, flat=1, up=2; false=0, true=1).
     */
    static DenseInstance toInstance(Instances dataset, List<String> header, String[] values) {
        DenseInstance inst = new DenseInstance(dataset.numAttributes());
        for (int i = 0; i < dataset.numAttributes(); i++) {
            if (i == dataset.classIndex()) continue;
            String name = dataset.attribute(i).name().toUpperCase(Locale.ENGLISH);
            int col = header.indexOf(name);
            if (col < 0) throw new IllegalArgumentException("Classifier attribute " + name + " not provided");
            if (col >= values.length || values[col].isEmpty()) throw new IllegalArgumentException("Missing value for " + name);
            inst.setValue(i, Double.parseDouble(values[col]));
        }
        inst.setDataset(dataset);
        return inst;
    }

    static String json(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }

    static String json(Collection<String> items) {
        StringJoiner j = new StringJoiner(",", "[", "]");
        for (String s : items) j.add(json(s));
        return j.toString();
    }

    /**
     * Resolve classes with this file's class loader. The source launcher compiles this file
     * in memory, so the default loader used by ObjectInputStream cannot see RoccaRFModel.
     */
    static class LocalObjectInputStream extends ObjectInputStream {
        LocalObjectInputStream(InputStream in) throws IOException { super(in); }
        @Override
        protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException, ClassNotFoundException {
            return Class.forName(desc.getName(), false, RoccaClassify.class.getClassLoader());
        }
    }
}

/**
 * Stand-in for PAMGuard's rocca.RoccaRFModel so that multi-stage model files can be
 * deserialised without PAMGuard. The class name, serialVersionUID and field names must
 * match PAMGuard's. PAMGuard's `roccaClassifier` field is deliberately left out: it is
 * only set while classifying, so it is null in saved model files and Java skips it.
 */
class RoccaRFModel implements Serializable {
    private static final long serialVersionUID = 01;

    AbstractClassifier roccaClassifierModel;
    Instances trainedDataset;
    RoccaRFModel[] modelList;
    String[] thisSpList;

    RoccaRFModel(AbstractClassifier classifier, Instances dataset, RoccaRFModel[] modelList) {
        this.roccaClassifierModel = classifier;
        this.trainedDataset = dataset;
        this.modelList = modelList;
        this.thisSpList = new String[dataset.numClasses()];
        for (int i = 0; i < dataset.numClasses(); i++) thisSpList[i] = dataset.classAttribute().value(i);
    }
}
