/**
 * Use Handlebar templates to generate HTML.
 */


/**
 * Fetches a JSON file and passes it to the callback function.
 *
 * @param {string} fileURL - URL to JSON file.
 * @param {textCallback} callback - Callback function that handles the response. If not specified
 *      then the request won't happen asynchronously and will only return once completed.
 */
function readJsonFile(fileURL, callback) {
    var rawFile = new XMLHttpRequest();
    rawFile.overrideMimeType("application/json");
    if (callback) {
        rawFile.onreadystatechange = function() {
            if (rawFile.readyState === 4 && rawFile.status == "200") {
                callback(rawFile.responseText);
            }
        }
    }
    rawFile.open("GET", fileURL, !(!callback));
    rawFile.send(null);
    return rawFile;
}


Handlebars.registerHelper('json', function(context) {
    return JSON.stringify(context);
});

Handlebars.registerHelper('isParent', function (value) {
    return value === 'husband' || value === 'wife';
});

Handlebars.registerHelper('personLink', function (value) {
    return `<div class="person">
        <a href="#${this.personId}"><span class="link-spanner"></span></a>
        ${this.firstName} ${this.lastName}
    </div>`;
});


const tblTemplate = Handlebars.compile(`
<h2>Relatives of {{person.firstName}} {{person.lastName}} ({{person.personId}})</h2>
{{#with relations}}
<table class="relations">
    <tr>
        <th>Parents:</th>
        {{#each child}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Siblings:</th>
        {{#each child}}
        <td colspan="2">
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
        </td>
        {{/each}}
    </tr>
    <tr>
        <th>Spouses/partners:</th>
        {{#each parent}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Children:</th>
        {{#each parent}}
        <td>
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
        </td>
        {{/each}}
    </tr>
</table>
{{/with}}
`);


function loadRelationData(familyLinks) {
    var relationData = {};
    familyLinks.forEach(link => {
        const familyId = link[0];
        const roleType = link[1];
        const familyType = link[2];
        const req = readJsonFile(`json/families/${familyId}.json`);
        if (req.status == 200) {
            var familyData = JSON.parse(req.response);
            if (relationData.hasOwnProperty(familyType)) {
                relationData[familyType].push(familyData)
            } else {
                relationData[familyType] = [familyData];
            }
        }
    });
    return relationData;
}


function removeSelfFromMembers(selfId, relationData) {
    Object.keys(relationData).forEach(type => {
        relationData[type].forEach(family => {
            const members = family['members'];
            const selfIdx = members.map(member => member['personId']).indexOf(selfId);
            if (selfIdx != -1) {
                members.splice(selfIdx, 1);
            }
        });
    });
}


function htmlRelations(personData, familyLinks) {
    var relationData = loadRelationData(familyLinks);
    removeSelfFromMembers(personData['personId'], relationData);
    console.log("Family tree data", relationData);
    return tblTemplate({ person: personData, relations: relationData });
}


function loadFamilyTree(personId) {
    personId = parseInt(personId);

    const req = readJsonFile(`json/people/${personId}.json`);
    var personData = { 'personId': personId };
    if (req.status == 200) {
        personData = JSON.parse(req.response);
    }

    readJsonFile("json/family-links.json", function(text){
        var familyLinks = JSON.parse(text);
        if (familyLinks.hasOwnProperty(personId)) {
            // console.log('Family links', familyLinks[personId]);
            const relations = document.getElementById("relatives");
            relations.innerHTML = htmlRelations(personData, familyLinks[personId]);
        } else {
            console.log('No family data for', personId);
            relations.innerHTML = `<span>No family data for ${personId}</span>`;
        }
    });
}


function main() {
    if (window.location.hash.length == 0) {
        // Set a default person to start with
        window.location.hash = '#19';
    } else {
        // Perform initial load since it isn't triggered by URL change
        loadFamilyTree(window.location.hash.substring(1));
    }
}


window.addEventListener('DOMContentLoaded', main, false);

// Detect changes in URL hash and reload family tree data 
window.addEventListener('hashchange',() => {
    loadFamilyTree(window.location.hash.substring(1));
});
