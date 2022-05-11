

function familyMemberToTreantNode(member) {
    return {
        text: { name: `${member.firstName} ${member.lastName}` },
        link: { href: `#${member.personId}` },
        HTMLclass: member.gender == "M" ? "tree-male" : (
            member.gender == "F" ? "tree-female" : ""),
    };
}


function treeConfigRelatives(personId, husband, wife, children, wife_only=false) {
    var nodes = [];
    const wifeNode = familyMemberToTreantNode(wife);
    const childrenNode = {
        HTMLclass: "tree-rel-link",
        text: { name: "" },
        stackChildren: wife_only,
        childrenDropLevel: 1,
        children: children.length == 0 ? undefined : children.map((child) => {
            var newNode = familyMemberToTreantNode(child);
            if (child.personId == personId) {
                newNode.HTMLclass = "tree-main-person";
            }
            return newNode;
        })
    };

    if (wife_only) {
        nodes.push({
            ...childrenNode,
            ...wifeNode,
        });
    } else {
        nodes.push(familyMemberToTreantNode(husband));
        nodes.push(childrenNode);
        nodes.push(wifeNode);
    }

    const chart_config = {
        chart: {
            container: "#parent-tree",
            rootOrientation: wife_only ? "NORTH" : "WEST",
            connectors: {
                type: "step"
            },
            hideRootNode: true,
            node: {
                HTMLclass: "tree-dark-box"
            }
        },
        nodeStructure: {
            text: { name: "root" },
            children: nodes,
        }
    };
    return chart_config;
}


function treeRelatives(personId, relativeData, familyType='ischild') {
    var husband = { personId: personId, roleType: "husband", firstName: "?", lastName: "" };
    var wife = { personId: personId, roleType: "wife", firstName: "?", lastName: "" };
    var children = [];
    // { personId: personId, roleType: "natural_child", firstName: "?", lastName: "" }

    if (relativeData[familyType] && relativeData[familyType].length > 0) {
        // ignore other parent families (e.g. later adoptions, etc.)
        var mainFamily = relativeData[familyType][0];
        husband = mainFamily.members.find(el => el.roleType == "husband");
        children = mainFamily.members.filter(el => el.roleType.endsWith("child"));
        wife = mainFamily.members.find(el => el.roleType == "wife");
    }
    const chart_config = treeConfigRelatives(personId, husband, wife, children,
        stack=(familyType == 'isparent'));
    return [chart_config, children.length];
}
