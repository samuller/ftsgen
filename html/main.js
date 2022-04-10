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
    return `<td style="position: relative">
        <a href="#${this.personId}"><span class="link-spanner"></span></a>
        ${this.firstName} ${this.lastName}
    </td>`;
});


const tblTemplate = Handlebars.compile(`
<h2>Relations of {{selfId}}</h2>
{{#with relations}}
<table class="relations">
    <tr>
        <th>Parents:</th>
        {{#each child}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        {{{personLink this}}}
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Siblings:</th>
        {{#each child}}
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
        {{/each}}
    </tr>
</table>

<table class="relations">
    <tr>
        <th>Spouses/partners:</th>
        {{#each parent}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        {{{personLink this}}}
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Children:</th>
        {{#each parent}}
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
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
            members.splice(selfIdx, 1);
        });
    });
}


function htmlRelations(currentPersonId, familyLinks) {
    var relationData = loadRelationData(familyLinks);
    removeSelfFromMembers(currentPersonId, relationData);
    console.log("relationData", relationData);
    return tblTemplate({ selfId: currentPersonId, relations: relationData });
}


function main() {
    var currentPersonId = 20;
    readJsonFile("json/family-links.json", function(text){
        var familyLinks = JSON.parse(text);
        if (familyLinks.hasOwnProperty(currentPersonId)) {
            console.log(familyLinks[currentPersonId]);
            const relations = document.getElementById("relations");
            relations.innerHTML = htmlRelations(currentPersonId, familyLinks[currentPersonId]);
        } else {
            console.log('No family data for', currentPersonId);
        }
    });
}


window.addEventListener('DOMContentLoaded', main, false);
