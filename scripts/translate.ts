import fs from "fs-extra";
import { resolve, basename, join } from "path";
import log from 'loglevel'
import { LLMConfig, translateCsvString, translateJsonDataToCsvString } from "../src/translate";
import { getLLMConfig, setupLog, getRemoteEndpoint } from "../src/setup-env"
import { program } from "commander";
import axios from "axios";
import { walkSync } from "@nodelib/fs.walk";
import { extractInfoFromCsvText } from "../src/csv";

// translate files in tmp
async function translateFolder(
  config,
  folder = "./tmp/untranslated",
  destFolder = "./tmp/translated",
  skipExisted = true,
  indexFile?: string, // ./index.json
) {
  const files = [];
  const entrys = walkSync(folder);

  let indexFileContent: { [key: string]: string } = {}
  
  if (indexFile) {
    indexFileContent = fs.readJsonSync(indexFile)
    log.info("Found " + Object.keys(indexFileContent).length + " csv files in index file")
  }


  for await (const entry of entrys) {
    if (entry.name.endsWith(".csv")) files.push(entry);
  }

  log.info("Found " + files.length + " csv files to translate");

  for (const entry of files) {
    log.info("Translating " + entry.name);
    const filePath = entry.path;

    if (entry.name.endsWith(".json")) {
      log.warn("JSON file is currently not supported");
      continue;
    }

    const csvString = await fs.promises.readFile(filePath, "utf-8");
    const csvInfo = extractInfoFromCsvText(csvString);

    if (indexFileContent[csvInfo.jsonUrl]) {
      log.debug(`Skipped ${csvInfo.jsonUrl} because of file already translated`);
      continue;
    }

    const destPath = resolve(destFolder, csvInfo.jsonUrl.replace(".txt", ".csv"));
    if (skipExisted && fs.existsSync(destPath)) {
      log.debug(`Skipped ${destPath} because of file existence`);
      continue;
    }

    if (entry.name.endsWith(".csv")) {
      try {
        const translatedCsvString = await translateCsvString(csvString, config);

        await fs.promises.writeFile(
          destPath,
          translatedCsvString,
          "utf-8"
        );
        log.info(`Output to ${destPath}`);
      } catch (error) {
        log.error(`failed to translate ${entry.path}`)
      }
    }
  }
}

async function getJsonPathList(diffEndpoint: string) {
  const assetMapDiff = (await axios.get(diffEndpoint)).data;
  return Object.keys(assetMapDiff.added).filter((file) => file.startsWith("json/"));
}

async function translateRemoteDiff(
  config: LLMConfig,
  diffEndpoint: string,
  assetEndpoint: string,
  destFolder: string = "./tmp/translated",
  skipExisted: boolean = true
) {
  const jsonPathList = await getJsonPathList(diffEndpoint);
  log.info("Found " + jsonPathList.length + " json files in latest diff to translate")

  for (const jsonPath of jsonPathList) {
    log.info("Translating " + jsonPath);
    const destPath = resolve(destFolder, basename(jsonPath).replaceAll(".json", ".csv"));
    if (skipExisted && fs.existsSync(destPath)) {
      log.debug(`Skipped ${destPath} because of file existence`);
      continue;
    }
    const jsonContent = (await axios.get(join(assetEndpoint, jsonPath))).data;
    log.debug(`translating json with ${jsonContent.length} frames`)
    const translatedCsvString = await translateJsonDataToCsvString(jsonContent, jsonPath.replace("json/", ""), config);
    await fs.writeFile(
      destPath,
      translatedCsvString,
      "utf-8"
    );
    log.info(`Output to ${destPath}`);
  }
}

async function main() {
  setupLog()
  program
    .requiredOption(
      "--type <translate-src-type>",
      "Type of the source file, can be folder, remote-diff",
      "folder"
    )
    .option(
      "--dir <dir>",
      "the source directory where the files are located, only activated when type is folder",
      "./tmp/untranslated"
  )
    .option(
      "--tag <tag>",
      "the version of the remote-diff, only activated when type is remote-diff",
      "-1"
    )
    .option(
      "--overwrite",
      "whether to overwrite translation if a translated file already exists, default to false (skip files)",
  )
    .option(
      "--indexfile <index-file>",
      "the index file used to ignore translated files",
      "./index.json"
  )
    .option(
      "--ignoreindex",
      "whether to ignore index files, default to false (always consider index file)",
    )
  await program.parseAsync(process.argv);
  const opts = program.opts();

  const config = getLLMConfig();
  if (opts.type === "folder") {
    log.info("Source File Directory:", opts.dir)
    log.info("overwrite files:", !!opts.overwrite);
    log.info("ignore index:", opts.ignoreindex);
    log.info("using index file:", opts.ignoreindex ? undefined : opts.indexfile);
    await translateFolder(config, opts.dir, opts.dest, !opts.overwrite, opts.ignoreindex?undefined:opts.indexfile);
  } else if (opts.type === "remote-diff") {
    const { diffEndpoint, assetEndpoint } = getRemoteEndpoint();
    log.info("Remote Diff Endpoint:", `${diffEndpoint}?latest=${opts.tag}`)
    log.info("overwrite files:", !!opts.overwrite)
    await translateRemoteDiff(
      config,
      `${diffEndpoint}?latest=${opts.tag}`,
      assetEndpoint,
      undefined,
      !opts.overwrite
    );
  }
}

main().then(() => {
  process.exit(0)
}).catch((err) => {
  log.error(err);
  process.exit(1);
})
